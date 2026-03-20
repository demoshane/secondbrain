"""Second Brain MCP server — FastMCP stdio transport."""
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from fastmcp import FastMCP
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.capture import build_post, capture_note, check_capture_dedup, log_audit, update_note, write_note_atomic
from engine.db import get_connection
from engine.digest import generate_digest
from engine.forget import forget_person
from engine.anonymize import anonymize_note
from engine.intelligence import find_similar, get_overdue_actions, list_actions, recap_entity
from engine.link_capture import fetch_link_metadata
from engine.paths import BRAIN_ROOT, CONFIG_PATH
from engine.router import get_adapter
from engine.search import search_hybrid, search_notes, search_semantic

try:
    from engine.intelligence import detect_git_context as _detect_git_context
except ImportError:
    _detect_git_context = None

mcp = FastMCP("second-brain")

# Token store for two-step destructive confirmation (MCP-04)
_pending: dict[str, float] = {}
_pending_lock = threading.Lock()

# MCP-07: Input size limits
_MAX_QUERY_LEN = 500
_MAX_TITLE_LEN = 200
_MAX_BODY_LEN = 50_000
_MAX_URL_LEN = 2048


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ensure_ready() -> None:
    """Fail fast with a clear message if the brain DB is not accessible.

    Raises RuntimeError within 5 s if the DB is locked or missing,
    instead of hanging until the MCP transport times out.
    """
    import sqlite3 as _sqlite3
    from engine.paths import DB_PATH as _DB_PATH
    try:
        conn = _sqlite3.connect(str(_DB_PATH), timeout=5)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:
        raise RuntimeError(
            f"BRAIN_NOT_READY: Cannot connect to brain database ({exc}). "
            "Is the second-brain API running? Start it with: sb-api"
        ) from exc


def _safe_path(raw: str) -> Path:
    """Resolve path and assert it is inside BRAIN_ROOT."""
    p = Path(raw).resolve()
    if not str(p).startswith(str(BRAIN_ROOT)):
        raise ValueError(f"PATH_OUTSIDE_BRAIN: {raw!r} is not inside the brain directory.")
    return p


def _log_mcp_audit(event: str, path: str) -> None:
    """Write audit row in its own connection — never reuses caller's conn."""
    conn = get_connection()
    try:
        log_audit(conn, event, path)
        conn.commit()
    finally:
        conn.close()


def _retry_call(fn, *args, **kwargs):
    """Wrap fn with tenacity: retry on transient SQLite/connection errors."""
    @retry(
        retry=retry_if_exception_type((sqlite3.OperationalError, ConnectionError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _inner():
        return fn(*args, **kwargs)
    return _inner()


# ---------------------------------------------------------------------------
# Two-step token helpers (MCP-04)
# ---------------------------------------------------------------------------

def _issue_token() -> str:
    tok = secrets.token_hex(16)
    with _pending_lock:
        _pending[tok] = time.time() + 60
    return tok


def _consume_token(tok: str) -> bool:
    with _pending_lock:
        expiry = _pending.pop(tok, None)
    return expiry is not None and time.time() < expiry


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

@mcp.tool()
def sb_search(query: str, mode: str = "hybrid", limit: int = 10) -> list[dict]:
    """Search brain notes by keyword, semantic, or hybrid mode."""
    _ensure_ready()
    if len(query) > _MAX_QUERY_LEN:
        raise ValueError(f"QUERY_TOO_LONG: query exceeds {_MAX_QUERY_LEN} characters.")
    valid_modes = {"hybrid", "semantic", "keyword"}
    if mode not in valid_modes:
        raise ValueError(f"INVALID_MODE: mode must be one of {valid_modes}.")
    conn = get_connection()
    try:
        if mode == "hybrid":
            results = _retry_call(search_hybrid, conn, query, limit)
        elif mode == "semantic":
            results = _retry_call(search_semantic, conn, query, limit)
        else:
            results = _retry_call(search_notes, conn, query, limit)
    finally:
        conn.close()
    _log_mcp_audit("mcp_search", query)
    return results


@mcp.tool()
def sb_capture(
    title: str,
    body: str,
    note_type: str = "note",
    tags: list[str] | None = None,
    sensitivity: str = "public",
    confirm_token: str = "",
) -> dict:
    """Capture a new note. Idempotent — identical title+body returns existing note.

    If a near-duplicate exists (cosine similarity >= 0.92), returns a duplicate_warning
    with a confirm_token. Pass that token back to save despite the similarity match.
    """
    _ensure_ready()
    if len(title) > _MAX_TITLE_LEN:
        raise ValueError(f"TITLE_TOO_LONG: title exceeds {_MAX_TITLE_LEN} characters.")
    if len(body) > _MAX_BODY_LEN:
        raise ValueError(f"BODY_TOO_LARGE: body exceeds {_MAX_BODY_LEN} characters.")
    conn = get_connection()
    try:
        # Dedup check: only when no confirm_token provided
        if not confirm_token:
            similar = check_capture_dedup(title, body, conn)
            if similar:
                tok = _issue_token()
                return {
                    "status": "duplicate_warning",
                    "message": f"Found {len(similar)} similar note(s). Pass confirm_token to save anyway.",
                    "similar": similar,
                    "confirm_token": tok,
                }
        elif not _consume_token(confirm_token):
            raise ValueError("TOKEN_EXPIRED: confirm_token is invalid or has expired (300s window)")

        path = capture_note(
            note_type=note_type,
            title=title,
            body=body,
            tags=tags or [],
            people=[],
            content_sensitivity=sensitivity,
            brain_root=BRAIN_ROOT,
            conn=conn,
        )
        conn.commit()
        _log_mcp_audit("mcp_capture", str(path))
        return {"status": "created", "path": str(path)}
    finally:
        conn.close()


@mcp.tool()
def sb_capture_batch(notes: list[dict]) -> dict:
    """Capture multiple notes in a single call. Each note is processed independently.

    Args:
        notes: List of note dicts. Each dict supports keys:
               title (required), body, note_type, tags, people, sensitivity.

    Returns:
        {"succeeded": [{"index": int, "path": str}, ...],
         "failed":    [{"index": int, "reason": str}, ...]}
    """
    from engine.capture import capture_note as _capture_note
    from engine.db import get_connection as _get_connection, init_schema as _init_schema
    from engine.paths import BRAIN_ROOT as _BRAIN_ROOT

    conn = _get_connection()
    _init_schema(conn)

    succeeded = []
    failed = []

    for i, note in enumerate(notes or []):
        try:
            title = note.get("title", "").strip()
            if not title:
                raise ValueError("title is required")
            body = note.get("body", "")
            note_type = note.get("note_type", "note")
            tags = [t.strip() for t in note.get("tags", "").split(",") if t.strip()] \
                   if isinstance(note.get("tags"), str) \
                   else list(note.get("tags") or [])
            people = [p.strip() for p in note.get("people", "").split(",") if p.strip()] \
                     if isinstance(note.get("people"), str) \
                     else list(note.get("people") or [])
            sensitivity = note.get("sensitivity", "public")

            path = _capture_note(note_type, title, body, tags, people, sensitivity, _BRAIN_ROOT, conn)
            succeeded.append({"index": i, "path": str(path)})
        except Exception as e:
            failed.append({"index": i, "reason": str(e)})

    conn.close()
    return {"succeeded": succeeded, "failed": failed}


@mcp.tool()
def sb_capture_link(
    url: str,
    tags: str | list[str] | None = None,
    people: str | list[str] | None = None,
    notes: str = "",
) -> dict:
    """Capture a URL as a link note. Fetches og:title and og:description automatically.
    Returns rich confirmation with fetched title and domain.
    If this URL was captured before, saves a new copy and warns via duplicate_url_warning status.
    """
    _ensure_ready()
    # URL validation: length and scheme checks (SSRF-01)
    if len(url) > _MAX_URL_LEN:
        raise ValueError("URL_TOO_LONG")
    from urllib.parse import urlparse as _urlparse
    _scheme = _urlparse(url).scheme
    if _scheme not in ("http", "https"):
        raise ValueError("INVALID_URL_SCHEME")
    # Coerce tags/people from string to list (MCP transport may JSON-serialize lists)
    import json as _json
    def _to_list(val):
        if val is None:
            return []
        if isinstance(val, list):
            return val
        val = val.strip()
        if val.startswith("["):
            try:
                return _json.loads(val)
            except (ValueError, TypeError):
                pass
        return [t.strip() for t in val.split(",") if t.strip()]
    tags = _to_list(tags)
    people = _to_list(people)
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname or url
    meta = fetch_link_metadata(url)
    title = meta["title"] or hostname
    description = meta["description"]
    body_parts = [description] if description else []
    if notes.strip():
        body_parts.append(notes.strip())
    body = "\n\n".join(body_parts)

    conn = get_connection()
    try:
        # Check if URL already captured — upsert if so
        existing = conn.execute(
            "SELECT path, title FROM notes WHERE url=? LIMIT 1", (url,)
        ).fetchone()

        if existing:
            existing_path = existing[0]
            update_note(
                note_path=existing_path,
                title=title,
                body=body,
                tags=tags,
                conn=conn,
                brain_root=BRAIN_ROOT,
            )
            _log_mcp_audit("mcp_update_link", existing_path)
            rel_path = str(existing_path).replace(str(BRAIN_ROOT) + "/", "")
            return {
                "status": "updated",
                "path": existing_path,
                "title": title,
                "domain": hostname,
                "message": f"Updated: '{title}' ({hostname}) → {rel_path}",
            }

        path = capture_note(
            note_type="link",
            title=title,
            body=body,
            tags=tags or [],
            people=people or [],
            content_sensitivity="public",
            brain_root=BRAIN_ROOT,
            conn=conn,
            url=url,
        )
        conn.commit()
        _log_mcp_audit("mcp_capture_link", str(path))

        rel_path = str(path).replace(str(BRAIN_ROOT) + "/", "")
        return {
            "status": "created",
            "path": str(path),
            "title": title,
            "domain": hostname,
            "message": f"Saved: '{title}' ({hostname}) → {rel_path}",
        }
    finally:
        conn.close()


@mcp.tool()
def sb_read(path: str) -> dict:
    """Read a note by absolute path."""
    p = _safe_path(path)
    content = p.read_text(encoding="utf-8")
    conn = get_connection()
    pii_flag = False
    try:
        row = conn.execute(
            "SELECT sensitivity FROM notes WHERE path=?", (str(p),)
        ).fetchone()
    finally:
        conn.close()
    if row and row[0] == "pii":
        # MCP-05: PII content routed through Ollama adapter before returning to caller.
        adapter = get_adapter("pii", CONFIG_PATH)
        content = adapter.summarize(content)
        pii_flag = True
    _log_mcp_audit("mcp_read", path)
    return {"content": content, "path": str(p), "pii": pii_flag}


@mcp.tool()
def sb_edit(path: str, body: str) -> dict:
    """Edit an existing note's body. Writes atomically."""
    import frontmatter as _fm
    p = _safe_path(path)
    if len(body) > _MAX_BODY_LEN:
        raise ValueError(f"BODY_TOO_LARGE: body exceeds {_MAX_BODY_LEN} characters.")
    if not p.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path!r} does not exist.")
    # Load existing frontmatter, update body, write atomically via engine helper
    post = _fm.load(str(p))
    post.content = body
    conn = get_connection()
    try:
        write_note_atomic(p, post, conn, update=True)
    finally:
        conn.close()
    _log_mcp_audit("mcp_edit", path)
    return {"status": "edited", "path": str(p)}


@mcp.tool()
def sb_recap(name: str | None = None) -> str:
    """Get session recap or cross-context synthesis for a person/project name."""
    import engine.mcp_server as _self
    if name is None and _detect_git_context is not None:
        name = _detect_git_context()
    if name is None:
        return "No recap available for this context."

    def _do_recap():
        conn = _self.get_connection()
        try:
            return recap_entity(name, conn)
        finally:
            conn.close()

    result = _retry_call(_do_recap)
    _log_mcp_audit("mcp_recap", name or "")
    return result or "No recap available for this context."


@mcp.tool()
def sb_digest() -> dict:
    """Generate or return the latest weekly digest."""
    digests_dir = BRAIN_ROOT / ".meta" / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    try:
        digest_path = _retry_call(generate_digest, conn, digests_dir)
    finally:
        conn.close()
    _log_mcp_audit("mcp_digest", str(digest_path))
    return {"path": str(digest_path), "status": "generated"}


@mcp.tool()
def sb_connections(path: str) -> list[dict]:
    """Return notes connected to the given note path."""
    p = _safe_path(path)
    conn = get_connection()
    try:
        results = find_similar(str(p), conn)
    finally:
        conn.close()
    _log_mcp_audit("mcp_connections", path)
    return results


@mcp.tool()
def sb_actions(done: bool = False) -> list[dict]:
    """List action items. done=True lists completed items."""
    conn = get_connection()
    try:
        results = list_actions(conn, done=done)
    finally:
        conn.close()
    _log_mcp_audit("mcp_actions", "")
    return results


@mcp.tool()
def sb_actions_done(action_id: int) -> dict:
    """Mark an action item as complete by ID."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "UPDATE action_items SET done=1, done_at=CURRENT_TIMESTAMP WHERE id=?",
            (action_id,),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"ACTION_NOT_FOUND: No action item with id={action_id}")
        _log_mcp_audit("mcp_actions_done", str(action_id))
        return {"status": "done", "id": action_id}
    finally:
        conn.close()


@mcp.tool()
def sb_files(subfolder: str | None = None) -> list[dict]:
    """List binary files in the brain, optionally filtered by subfolder."""
    files_dir = BRAIN_ROOT / "files"
    if not files_dir.exists():
        raise ValueError(f"FILES_DIR_NOT_FOUND: {files_dir} does not exist.")
    search_root = files_dir / subfolder if subfolder else files_dir
    results = []
    for f in sorted(search_root.rglob("*")):
        if f.is_file():
            rel = f.relative_to(files_dir)
            results.append({
                "name": f.name,
                "path": str(f),
                "subfolder": str(rel.parent) if rel.parent != Path(".") else "",
            })
    _log_mcp_audit("mcp_files", str(files_dir))
    return results


@mcp.tool()
def sb_forget(slug: str, confirm_token: str = "") -> dict:
    """Forget all data for a person. Call once to get token; call again with token within 60s."""
    if not confirm_token:
        tok = _issue_token()
        return {
            "status": "pending",
            "confirm_token": tok,
            "message": f"Call sb_forget again with confirm_token='{tok}' within 60 seconds to execute.",
        }
    if not _consume_token(confirm_token):
        raise ValueError(
            "TOKEN_EXPIRED: confirm_token is invalid or expired. "
            "Call sb_forget without a token to get a new one."
        )
    conn = get_connection()
    try:
        result = forget_person(slug, BRAIN_ROOT, conn)
        conn.commit()
        _log_mcp_audit("mcp_forget", slug)
        return result
    finally:
        conn.close()


@mcp.tool()
def sb_anonymize(path: str, tokens: list[str] | None = None, confirm_token: str = "") -> dict:
    """Anonymize a note. Call once to get confirmation token; call again with token within 60s."""
    p = _safe_path(path)
    if not confirm_token:
        tok = _issue_token()
        return {
            "status": "pending",
            "confirm_token": tok,
            "message": f"Call sb_anonymize again with confirm_token='{tok}' within 60 seconds to execute.",
        }
    if not _consume_token(confirm_token):
        raise ValueError(
            "TOKEN_EXPIRED: confirm_token is invalid or expired. "
            "Call sb_anonymize without a token to get a new one."
        )
    conn = get_connection()
    try:
        result = anonymize_note(p, tokens or [], conn)
        conn.commit()
        _log_mcp_audit("mcp_anonymize", path)
        return result
    finally:
        conn.close()


@mcp.tool()
def sb_capture_smart(content: str) -> dict:
    """Classify freeform text into 1-N typed note suggestions without saving anything.

    Returns suggestions with title, type, body, and cross-links inferred from the
    content. Pass the suggestions list to sb_capture_batch to commit them.

    Args:
        content: Freeform text to classify and segment.

    Returns:
        {"suggestions": [{"title": str, "type": str, "body": str, "links": [str]}, ...],
         "confirm_token": str,
         "hint": str}
    """
    import re as _re

    def _classify_segment(segment: str) -> str:
        low = segment.lower()
        if _re.search(r"meeting|discussed|attendees|agenda", low):
            return "meeting"
        # Person: Name-like pattern + contact/role signal in first 200 chars
        if _re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", segment[:200]) and \
                _re.search(r"role|contact|email|phone|linkedin", low):
            return "person"
        if _re.search(r"project|milestone|deadline|sprint|roadmap", low):
            return "project"
        if _re.search(r"idea|what if|maybe|consider|brainstorm", low):
            return "idea"
        return "note"

    def _derive_title(segment: str) -> str:
        for line in segment.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:80]
        return "Untitled"

    def _slugify(title: str) -> str:
        import re as _re2
        return _re2.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")

    # Segment: split by double newline if content is >= 500 chars, else single segment
    if len(content) < 500:
        raw_segments = [content]
    else:
        raw_segments = [s.strip() for s in content.split("\n\n") if s.strip()]
        if not raw_segments:
            raw_segments = [content]

    suggestions = []
    for seg in raw_segments:
        note_type = _classify_segment(seg)
        title = _derive_title(seg)
        suggestions.append({
            "title": title,
            "type": note_type,
            "body": seg,
            "links": [],
        })

    # Infer cross-links: if meeting + person both present, link person slugs into meeting
    if len(suggestions) > 1:
        person_slugs = [
            _slugify(s["title"]) for s in suggestions if s["type"] == "person"
        ]
        for s in suggestions:
            if s["type"] == "meeting" and person_slugs:
                s["links"] = person_slugs

    confirm_token = _issue_token()
    return {
        "suggestions": suggestions,
        "confirm_token": confirm_token,
        "hint": "Call sb_capture_batch with suggestions to save.",
    }



@mcp.tool()
def sb_remind(action_id: int, due_date: str | None = None) -> dict:
    """Set or clear a due date on an action item. due_date format: YYYY-MM-DD. Pass None to clear."""
    conn = get_connection()
    try:
        conn.execute("UPDATE action_items SET due_date=? WHERE id=?", (due_date, action_id))
        conn.commit()
        return {"updated": True, "action_id": action_id, "due_date": due_date}
    finally:
        conn.close()


def _save_tags(note_path, new_tags: list, abs_path: str, conn) -> None:
    """Write tags to frontmatter on disk (atomic) and update notes.tags in DB."""
    import json
    import tempfile
    import os
    import frontmatter as _fm

    post = _fm.load(str(note_path))
    post["tags"] = new_tags
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=str(note_path.parent),
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(_fm.dumps(post).encode("utf-8"))
        tmp_name = tmp.name
    os.replace(tmp_name, str(note_path))
    conn.execute("UPDATE notes SET tags=? WHERE path=?", (json.dumps(new_tags), abs_path))


@mcp.tool()
def sb_tag(path: str, action: str, tag: str, confirm_token: str = "") -> dict:
    """Add or remove a tag on a note with fuzzy matching and confirm-token gate for new tags.

    action must be "add" or "remove".

    For "add":
    - If the tag fuzzy-matches an existing tag (cutoff 0.8), the existing tag is used immediately.
    - If the tag is brand-new and no confirm_token provided, returns {confirm_token: ..., message: ...}.
    - If confirm_token is provided, validates it and saves the new tag.

    For "remove":
    - Removes the tag (case-insensitive). No confirm-token needed.
    """
    import difflib
    import json

    if action not in ("add", "remove"):
        raise ValueError(f"INVALID_ACTION: action must be 'add' or 'remove', got {action!r}")

    p = _safe_path(path)
    if not p.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path!r} does not exist.")

    conn = get_connection()
    try:
        if action == "remove":
            row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(p),)).fetchone()
            current_tags = json.loads((row[0] if row else None) or "[]")
            new_tags = [t for t in current_tags if t.lower() != tag.lower()]
            final_tag = tag
            _save_tags(p, new_tags, str(p), conn)
            conn.commit()
            _log_mcp_audit("mcp_tag_remove", str(p))
            return {"path": str(p), "action": action, "tag": final_tag, "tags": new_tags}

        # "add" path -- gather all existing tags from DB
        rows = conn.execute(
            "SELECT DISTINCT j.value FROM notes, json_each(notes.tags) AS j WHERE notes.tags IS NOT NULL"
        ).fetchall()
        all_existing = [r[0] for r in rows if r[0]]

        matches = difflib.get_close_matches(tag, all_existing, n=1, cutoff=0.8)

        if matches:
            # Fuzzy match found -- use existing tag immediately, no confirm needed
            final_tag = matches[0]
            row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(p),)).fetchone()
            current_tags = json.loads((row[0] if row else None) or "[]")
            new_tags = list(dict.fromkeys(current_tags + [final_tag]))
            _save_tags(p, new_tags, str(p), conn)
            conn.commit()
            _log_mcp_audit("mcp_tag_add", str(p))
            return {
                "path": str(p), "action": action, "tag": final_tag, "tags": new_tags,
                "matched": final_tag, "applied": True,
            }

        # Brand-new tag -- gate with confirm-token
        if not confirm_token:
            tok = _issue_token()
            return {
                "confirm_token": tok,
                "message": f"'{tag}' is a new tag. Call again with confirm_token to create.",
            }
        if not _consume_token(confirm_token):
            raise ValueError("TOKEN_EXPIRED: confirm_token is invalid or has expired.")

        final_tag = tag
        row = conn.execute("SELECT tags FROM notes WHERE path=?", (str(p),)).fetchone()
        current_tags = json.loads((row[0] if row else None) or "[]")
        new_tags = list(dict.fromkeys(current_tags + [final_tag]))
        _save_tags(p, new_tags, str(p), conn)
        conn.commit()
        _log_mcp_audit("mcp_tag_add", str(p))
        return {"path": str(p), "action": action, "tag": final_tag, "tags": new_tags}
    finally:
        conn.close()


@mcp.tool()
def sb_tools() -> list[dict]:
    """List all available MCP tools with their input schemas.

    Use this to discover what operations are available without needing external documentation.

    Returns:
        List of {name, description, parameters, output_schema} dicts, one per tool.
        sb_tools itself is excluded to prevent infinite agent loops.
    """
    try:
        # Avoid asyncio.run() — FastMCP stdio runs in an existing event loop.
        # _local_provider._components is a sync dict keyed as "tool:<name>@".
        components = mcp._local_provider._components
        tools = [v for k, v in components.items() if k.startswith("tool:")]
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.parameters if hasattr(t, "parameters") else {},
                "output_schema": t.output_schema if hasattr(t, "output_schema") else {},
            }
            for t in tools
            if t.name != "sb_tools"
        ]
    except AttributeError:
        return [{"name": "sb_tools", "description": "Tool introspection unavailable", "parameters": {}}]


@mcp.tool()
def sb_link(source_path: str, target_path: str, rel_type: str = "link") -> dict:
    """Create a directional relationship between two notes. DB-only — does not edit note bodies.

    rel_type: arbitrary string label, default 'link'.
    Common values: 'link', 'references', 'similar', 'part-of'.
    Idempotent — calling with the same (source, target, rel_type) twice inserts only one row.
    """
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
            (source_path, target_path, rel_type),
        )
        conn.commit()
        return {"linked": True, "source": source_path, "target": target_path, "rel_type": rel_type}
    finally:
        conn.close()


@mcp.tool()
def sb_unlink(source_path: str, target_path: str, rel_type: str | None = None) -> dict:
    """Remove a directional relationship between two notes. DB-only — does not edit note bodies.

    If rel_type is None, removes all relationships between source and target regardless of type.
    Absent pair is a no-op — returns success without raising an error.
    """
    conn = get_connection()
    try:
        if rel_type is not None:
            conn.execute(
                "DELETE FROM relationships WHERE source_path=? AND target_path=? AND rel_type=?",
                (source_path, target_path, rel_type),
            )
        else:
            conn.execute(
                "DELETE FROM relationships WHERE source_path=? AND target_path=?",
                (source_path, target_path),
            )
        conn.commit()
        return {"unlinked": True, "source": source_path, "target": target_path}
    finally:
        conn.close()


@mcp.tool()
def sb_person_context(name_or_path: str) -> dict:
    """Return full context for a person: note body, meetings, actions, mentions, and relationship metrics.

    Accepts either a direct note path ("/brain/people/alice.md") or a person name ("Alice Smith").
    Uses the people column (json_each) for lookups — not body text scan.

    Returns:
        On success: {found, path, note, meetings, actions, mentions, org, last_interaction_date,
                     total_meetings, total_mentions, total_actions}
        On failure: {found: False, error: str}
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        # 1. Resolve person path from name or direct path
        if "/" in name_or_path:
            person_path = name_or_path
            row = conn.execute(
                "SELECT title, body, entities FROM notes WHERE path=? AND type IN ('person','people')",
                (person_path,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT path, title, body, entities FROM notes "
                "WHERE LOWER(title)=LOWER(?) AND type IN ('person','people') LIMIT 1",
                (name_or_path,),
            ).fetchone()
            if row is None:
                return {"found": False, "error": f"Person not found: {name_or_path!r}"}
            person_path = row["path"]

        if row is None:
            return {"found": False, "error": f"Person not found: {name_or_path!r}"}

        person_title = row["title"]

        # 2. Meetings via json_each people column (exact path OR name-like match)
        meeting_rows = conn.execute(
            """
            SELECT DISTINCT n.path, n.title, n.created_at
            FROM notes n, json_each(COALESCE(n.people, '[]')) pe
            WHERE (pe.value = ? OR pe.value LIKE ?)
              AND n.type = 'meeting'
            ORDER BY n.created_at DESC
            """,
            (person_path, f"%{person_title}%"),
        ).fetchall()
        meetings = [
            {"path": r["path"], "title": r["title"], "meeting_date": (r["created_at"] or "")[:10]}
            for r in meeting_rows
        ]

        # 3. Mentions (non-person/meeting notes) via json_each people column
        mention_rows = conn.execute(
            """
            SELECT DISTINCT n.path, n.title, n.created_at
            FROM notes n, json_each(COALESCE(n.people, '[]')) pe
            WHERE (pe.value = ? OR pe.value LIKE ?)
              AND n.type NOT IN ('person', 'people', 'meeting')
            ORDER BY n.created_at DESC
            """,
            (person_path, f"%{person_title}%"),
        ).fetchall()
        mentions = [{"path": r["path"], "title": r["title"]} for r in mention_rows]

        # 4. Action items: assigned to person path or mentioning name; ordered by due_date then created_at
        assigned_rows = conn.execute(
            "SELECT id, text, done, due_date, note_path FROM action_items "
            "WHERE assignee_path=? ORDER BY due_date ASC, id ASC",
            (person_path,),
        ).fetchall()
        seen_ids: set = {r["id"] for r in assigned_rows}

        mentioned_rows = conn.execute(
            "SELECT id, text, done, due_date, note_path FROM action_items "
            "WHERE text LIKE ? ORDER BY due_date ASC, id ASC",
            (f"%{person_title}%",),
        ).fetchall()

        def _row_to_action(r) -> dict:
            keys = r.keys()
            return {
                "id": r["id"],
                "text": r["text"],
                "done": r["done"],
                "due_date": r["due_date"] if "due_date" in keys else None,
                "note_path": r["note_path"] if "note_path" in keys else None,
            }

        actions = [_row_to_action(r) for r in assigned_rows]
        for r in mentioned_rows:
            if r["id"] not in seen_ids:
                actions.append(_row_to_action(r))
                seen_ids.add(r["id"])

        # 5. Enrichment metrics
        import json as _json
        ents = _json.loads(row["entities"] or "{}")
        org = (ents.get("orgs") or [""])[0]

        all_dates = [r["created_at"] for r in meeting_rows] + [r["created_at"] for r in mention_rows]
        last_interaction_date = max((d for d in all_dates if d), default=None)
        if last_interaction_date:
            last_interaction_date = last_interaction_date[:10]

        return {
            "found": True,
            "path": person_path,
            "note": {"title": person_title, "body": row["body"]},
            "meetings": meetings,
            "actions": actions,
            "mentions": mentions,
            "org": org,
            "last_interaction_date": last_interaction_date,
            "total_meetings": len(meetings),
            "total_mentions": len(mentions),
            "total_actions": len(actions),
        }
    finally:
        conn.close()



def main() -> None:
    mcp.run(transport="stdio")
