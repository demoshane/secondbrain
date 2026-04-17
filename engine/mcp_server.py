"""Second Brain MCP server — FastMCP stdio transport."""
import datetime
import logging
import math
import secrets
import sqlite3
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

from fastmcp import FastMCP
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.capture import build_post, capture_note, check_capture_dedup, log_audit, update_note, write_note_atomic
from engine.db import get_connection, PERSON_TYPES, PERSON_TYPES_PH, _escape_like, _json_list, touch_note_access
from engine.digest import generate_digest
from engine.forget import forget_person
from engine.anonymize import anonymize_note
from engine.intelligence import find_dormant_related, find_similar, find_temporal_neighbors, get_overdue_actions, list_actions, recap_entity, surface_relevant
from engine.link_capture import fetch_link_metadata
from engine.links import traverse_graph
from engine.paths import BRAIN_ROOT, CONFIG_PATH, store_path
from engine.router import get_adapter
from engine.search import search_hybrid, search_notes, search_semantic, _apply_filters

try:
    from engine.intelligence import detect_git_context as _detect_git_context
except ImportError:
    _detect_git_context = None

mcp = FastMCP("second-brain")

# Token store for two-step destructive confirmation (MCP-04)
_pending: dict[str, float] = {}
_pending_lock = threading.Lock()


def _spawn_background(target):
    """Spawn a daemon thread. Patchable in tests without touching stdlib threading."""
    def _safe():
        try:
            target()
        except Exception:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "background task %s crashed", getattr(target, "__name__", "?"), exc_info=True
            )
    threading.Thread(target=_safe, daemon=True).start()


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
    """Resolve path and assert it is inside BRAIN_ROOT. Returns absolute Path."""
    p = Path(raw).resolve()
    if not str(p).startswith(str(BRAIN_ROOT)):
        raise ValueError(f"PATH_OUTSIDE_BRAIN: {raw!r} is not inside the brain directory.")
    return p


def _resolve(raw: str) -> "ResolvedPath":
    """Resolve path, validate inside BRAIN_ROOT, return both absolute and relative forms.

    This is the preferred boundary function for MCP tools — eliminates the
    _safe_path() + store_path() round-trip at every call site.
    """
    from engine.paths import ResolvedPath
    p = Path(raw).resolve()
    if not str(p).startswith(str(BRAIN_ROOT)):
        raise ValueError(f"PATH_OUTSIDE_BRAIN: {raw!r} is not inside the brain directory.")
    return ResolvedPath(absolute=p, relative=store_path(p))


def _log_mcp_audit(event: str, path: str) -> None:
    """Write audit row in its own connection — never reuses caller's conn."""
    conn = get_connection()
    try:
        log_audit(conn, event, path)
        conn.commit()
    finally:
        conn.close()


def _auto_co_capture(conn, new_path: str, created_at: str, capture_session: str | None = None) -> list[dict]:
    """Find temporal neighbors + same-session notes, create co-captured relationships.

    Returns list of all linked notes (temporal + session-based) for response nudges.
    """
    neighbors = find_temporal_neighbors(conn, created_at, exclude_path=new_path)
    neighbor_map = {n["path"]: n for n in neighbors}

    # Also find same-session notes if a capture_session is provided
    if capture_session:
        rows = conn.execute(
            "SELECT path, title, type, created_at FROM notes WHERE capture_session = ? AND path != ?",
            (capture_session, new_path),
        ).fetchall()
        for r in rows:
            if r[0] not in neighbor_map:
                neighbor_map[r[0]] = {
                    "path": r[0], "title": r[1], "type": r[2],
                    "created_at": r[3], "delta_seconds": 0,
                }

    for target_path in neighbor_map:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                (new_path, target_path, "co-captured"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                (target_path, new_path, "co-captured"),
            )
        except Exception:
            logger.debug("co-captured relationship insert skipped", exc_info=True)

    if neighbor_map:
        conn.commit()

    return list(neighbor_map.values())


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
        _pending[tok] = time.monotonic() + 60
    return tok


def _consume_token(tok: str) -> bool:
    with _pending_lock:
        expiry = _pending.pop(tok, None)
    return expiry is not None and time.monotonic() < expiry


def _to_list(val) -> list:
    """Coerce MCP transport values to list. MCP may send list[str] as a JSON string."""
    import json as _json
    if val is None:
        return []
    if isinstance(val, list):
        return val
    val = str(val).strip()
    if val.startswith("["):
        try:
            return _json.loads(val)
        except (ValueError, TypeError):
            pass
    return [t.strip() for t in val.split(",") if t.strip()]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

@mcp.tool()
def sb_search(
    query: str,
    mode: str = "hybrid",
    limit: int = 10,
    page: int = 1,
    person: str | None = None,
    tag: str | None = None,
    note_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    importance: str | None = None,
    context_hint: str | None = None,
) -> dict:
    """Search brain notes by keyword, semantic, or hybrid mode.

    Optional entity filters narrow results with AND logic:
    - person: match notes where person appears in the people column
    - tag: match notes with this tag in the note_tags junction table
    - note_type: match notes with this exact type value
    - from_date: ISO date string YYYY-MM-DD — exclude notes created before this date
    - to_date: ISO date string YYYY-MM-DD — exclude notes created after this date
    - context_hint: optional free-text describing conversation context. When provided,
      appends 2-3 proactive suggestions (notes you didn't search for but may be relevant).
    """
    _ensure_ready()
    if len(query) > _MAX_QUERY_LEN:
        raise ValueError(f"QUERY_TOO_LONG: query exceeds {_MAX_QUERY_LEN} characters.")
    valid_modes = {"hybrid", "semantic", "keyword"}
    if mode not in valid_modes:
        raise ValueError(f"INVALID_MODE: mode must be one of {valid_modes}.")
    page = max(1, page)
    limit = min(limit, 200)
    conn = get_connection()
    try:
        if mode == "hybrid":
            all_results = _retry_call(search_hybrid, conn, query, limit * page)
        elif mode == "semantic":
            all_results = _retry_call(search_semantic, conn, query, limit * page)
        else:
            all_results = _retry_call(search_notes, conn, query, limit * page)
        # Apply entity filters (person, tag, note_type, from_date, to_date) — AND logic
        all_results = _apply_filters(
            all_results, conn,
            person=person,
            tag=tag,
            note_type=note_type,
            from_date=from_date,
            to_date=to_date,
            importance=importance,
        )
    finally:
        conn.close()
    total = len(all_results)
    offset = (page - 1) * limit
    results = all_results[offset:offset + limit]
    total_pages = math.ceil(total / limit) if limit else 1
    _log_mcp_audit("mcp_search", query)
    response = {"results": results, "total": total, "page": page, "total_pages": total_pages}

    # Proactive suggestions when context_hint is provided
    if context_hint:
        try:
            conn2 = get_connection()
            try:
                suggestions = surface_relevant(conn2, context_hint, max_results=3)
                # Remove duplicates with primary results
                result_paths = {r["path"] for r in results}
                suggestions = [s for s in suggestions if s["path"] not in result_paths]
                response["proactive_suggestions"] = suggestions
            finally:
                conn2.close()
        except Exception:
            response["proactive_suggestions"] = []

    return response


@mcp.tool()
def sb_capture(
    title: str,
    body: str,
    note_type: str = "note",
    tags: str | list[str] | None = None,
    sensitivity: str = "public",
    confirm_token: str = "",
    importance: str = "medium",
    session_id: str = "",
) -> dict:
    """Capture a new note. Idempotent — identical title+body returns existing note.

    If a near-duplicate exists (cosine similarity >= 0.92), returns a duplicate_warning
    with a confirm_token. Pass that token back to save despite the similarity match.

    IMPORTANT — session_id usage:
    Generate ONE session UUID at the start of any conversation that involves captures.
    Pass the SAME session_id to every sb_capture call in that conversation thread.
    If the user continues the same topic in a later conversation (even days later),
    reuse the same session_id. This groups related captures across time — they are
    auto-linked as co-captured regardless of time gap.

    Without session_id, captures are linked by temporal proximity only (15-minute window).
    With session_id, captures are linked by shared context even across days.

    Args:
        session_id: UUID to group captures from the same conversation thread.
                    Generate once per topic, reuse across calls and sessions.
                    Notes sharing a session_id are auto-linked as co-captured.
    """
    _ensure_ready()
    tags = _to_list(tags)
    if len(title) > _MAX_TITLE_LEN:
        raise ValueError(f"TITLE_TOO_LONG: title exceeds {_MAX_TITLE_LEN} characters.")
    if len(body) > _MAX_BODY_LEN:
        raise ValueError(f"BODY_TOO_LARGE: body exceeds {_MAX_BODY_LEN} characters.")
    conn = get_connection()
    try:
        # Dedup check: only when no confirm_token provided
        similar_paths_for_link: list[str] = []
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
        else:
            if not _consume_token(confirm_token):
                raise ValueError("TOKEN_EXPIRED: confirm_token is invalid or has expired (300s window)")
            # Re-run dedup to find which notes to auto-link as 'similar'
            similar_for_link = check_capture_dedup(title, body, conn)
            similar_paths_for_link = [s["path"] for s in similar_for_link]

        # Auto-classify sensitivity (never downgrade)
        from engine.smart_classifier import classify_smart as _cs
        effective_sensitivity, _sensitivity_reason = _cs(body, sensitivity)

        if importance not in ("low", "medium", "high"):
            raise ValueError("importance must be low, medium, or high")
        _cap_session = session_id or None
        path = capture_note(
            note_type=note_type,
            title=title,
            body=body,
            tags=tags or [],
            people=[],
            content_sensitivity=effective_sensitivity,
            brain_root=BRAIN_ROOT,
            conn=conn,
            importance=importance,
            capture_session=_cap_session,
        )
        conn.commit()

        # Auto-link as 'similar' when user confirmed despite dedup warning
        import datetime as _dt
        now_ts = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
        src_path = store_path(path.resolve())
        for _sp in similar_paths_for_link:
            try:
                _sp_norm = store_path(Path(_sp).resolve()) if Path(_sp).is_absolute() else _sp
                conn.execute(
                    "INSERT OR IGNORE INTO relationships "
                    "(source_path, target_path, rel_type, created_at) VALUES (?,?,?,?)",
                    (src_path, _sp_norm, "similar", now_ts),
                )
            except Exception:
                logger.debug("relationship insert skipped", exc_info=True)
        if similar_paths_for_link:
            conn.commit()

        # Dormant resurfacing — best-effort, never blocks
        dormant_notes: list[dict] = []
        try:
            dormant_notes = find_dormant_related(src_path, conn)
        except Exception:
            logger.debug("dormant resurfacing skipped", exc_info=True)

        # Phase 56: auto co-capture with temporal neighbors + nudges
        co_captured_with: list[str] = []
        recent_context: list[dict] = []
        try:
            neighbors = _auto_co_capture(conn, src_path, now_ts, _cap_session)
            co_captured_with = [n["path"] for n in neighbors]
            recent_context = [
                {"path": n["path"], "title": n["title"], "type": n["type"],
                 "minutes_ago": max(1, n["delta_seconds"] // 60)}
                for n in neighbors
            ]
        except Exception:
            logger.debug("auto co-capture skipped", exc_info=True)

        nudge = ""
        if len(co_captured_with) == 1:
            _t = recent_context[0]["title"] if recent_context else co_captured_with[0]
            nudge = f"Auto-linked with recent capture: {_t}"
        elif len(co_captured_with) > 1:
            nudge = f"Auto-linked with {len(co_captured_with)} recent captures from this session."

        _log_mcp_audit("mcp_capture", str(path))
        result = {
            "status": "created",
            "path": str(path),
            "dormant_notes": dormant_notes,
            "co_captured_with": co_captured_with,
            "recent_context": recent_context,
        }
        if nudge:
            result["nudge"] = nudge
        return result
    finally:
        conn.close()


@mcp.tool()
def sb_capture_batch(notes: list[dict]) -> dict:
    """Capture multiple notes in a single call. Each note is processed independently.

    After saving, intelligence hooks (check_connections + extract_action_items) run
    asynchronously in a background daemon thread — the response returns immediately.
    Hook errors are caught and logged to audit_log with action='intelligence_error'.

    Args:
        notes: List of note dicts. Each dict supports keys:
               title (required), body, note_type, tags, people, sensitivity.

    Returns:
        {"succeeded": [{"index": int, "path": str}, ...],
         "failed":    [{"index": int, "reason": str}, ...]}
    """
    import datetime as _dt
    import difflib as _difflib
    from engine.capture import capture_note as _capture_note, check_capture_dedup as _check_dedup
    from engine.db import get_connection as _get_connection, init_schema as _init_schema
    from engine.paths import BRAIN_ROOT as _BRAIN_ROOT
    from engine.smart_classifier import classify_smart as _classify_smart

    import uuid as _uuid

    conn = _get_connection()
    _init_schema(conn)

    capture_session = str(_uuid.uuid4())
    succeeded = []
    failed = []
    dedup_warnings = []
    seen_titles: list[str] = []

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
            user_sensitivity = note.get("sensitivity", "public")
            importance = note.get("importance", "medium")

            # Auto-classify sensitivity (never downgrade)
            effective_sensitivity, _reason = _classify_smart(body, user_sensitivity)

            # Per-note dedup check (informational, not blocking)
            if len(body.strip()) >= 50:
                try:
                    similar = _check_dedup(title, body, conn)
                    if similar:
                        dedup_warnings.append({"index": i, "similar": similar})
                except Exception:
                    logger.debug("relationship insert skipped", exc_info=True)

            # Intra-batch title dedup
            matches = _difflib.get_close_matches(title, seen_titles, n=1, cutoff=0.85)
            if matches:
                dedup_warnings.append({"index": i, "intra_batch_match": matches[0]})

            path = _capture_note(note_type, title, body, tags, people, effective_sensitivity, _BRAIN_ROOT, conn, importance=importance, capture_session=capture_session)
            succeeded.append({"index": i, "path": str(path)})
            seen_titles.append(title)
        except Exception as e:
            failed.append({"index": i, "reason": str(e)})

    # Post-save: process links field and create relationships
    # Normalize captured paths to relative DB paths for relationship storage
    path_map = {}
    for s in succeeded:
        try:
            path_map[s["index"]] = store_path(Path(s["path"]).resolve())
        except (ValueError, KeyError):
            path_map[s["index"]] = s["path"]
    for i, note in enumerate(notes or []):
        if i not in path_map:
            continue
        links = note.get("links", [])
        if not links:
            continue
        for slug in links:
            row = conn.execute(
                "SELECT path FROM notes WHERE LOWER(title) = LOWER(?) LIMIT 1",
                (slug.replace("-", " "),)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT path FROM notes WHERE path LIKE ? LIMIT 1",
                    (f"%{slug}%",)
                ).fetchone()
            if row:
                now = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
                conn.execute(
                    "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
                    (path_map[i], row[0], "link"),
                )
                conn.execute(
                    "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
                    (row[0], path_map[i], "link"),
                )
    # Phase 56: intra-batch co-captured relationships + temporal neighbors
    import itertools as _itertools
    batch_db_paths = list(path_map.values())
    for src, tgt in _itertools.combinations(batch_db_paths, 2):
        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                (src, tgt, "co-captured"),
            )
        except Exception:
            logger.debug("co-captured relationship insert skipped", exc_info=True)

    # Link with temporal neighbors outside the batch
    now_ts = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
    batch_path_set = set(batch_db_paths)
    for db_path in batch_db_paths:
        try:
            neighbors = find_temporal_neighbors(conn, now_ts, exclude_path=db_path)
            for n in neighbors:
                if n["path"] not in batch_path_set:
                    conn.execute(
                        "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                        (db_path, n["path"], "co-captured"),
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                        (n["path"], db_path, "co-captured"),
                    )
        except Exception:
            logger.debug("temporal neighbor linking skipped", exc_info=True)

    conn.commit()
    conn.close()

    # Spawn background daemon thread for intelligence hooks — never blocks the response
    _saved_paths = [s["path"] for s in succeeded]
    _brain_root_for_hooks = _BRAIN_ROOT

    def _run_batch_intelligence() -> None:
        from engine.intelligence import (
            check_connections as _check_connections,
            extract_action_items as _extract_action_items,
        )

        def _log_intel_error(p: str, exc: Exception) -> None:
            try:
                _ec = _get_connection()
                _ec.execute(
                    "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?,?,?,?)",
                    (
                        "intelligence_error",
                        p,
                        str(exc),
                        _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    ),
                )
                _ec.commit()
                _ec.close()
            except Exception:
                logger.debug("non-fatal operation skipped", exc_info=True)

        for p in _saved_paths:
            # DB stores relative paths — convert for lookups
            try:
                _db_p = store_path(Path(p).resolve())
            except (ValueError, Exception):
                _db_p = p

            # check_connections
            try:
                _c = _get_connection()
                try:
                    _check_connections(Path(p), _c, _brain_root_for_hooks)
                    _c.commit()
                finally:
                    _c.close()
            except Exception as exc:
                _log_intel_error(p, exc)

            # extract_action_items
            try:
                _c2 = _get_connection()
                try:
                    row = _c2.execute("SELECT body FROM notes WHERE path=?", (_db_p,)).fetchone()
                    if row and row[0]:
                        _extract_action_items(Path(p), row[0], "public", _c2)
                finally:
                    _c2.close()
            except Exception as exc:
                _log_intel_error(p, exc)

    _spawn_background(target=_run_batch_intelligence)

    return {"succeeded": succeeded, "failed": failed, "dedup_warnings": dedup_warnings, "capture_session": capture_session}


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
    tags_provided = tags is not None
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
            "SELECT path, title, tags FROM notes WHERE url=? LIMIT 1", (url,)
        ).fetchone()

        if existing:
            existing_path = existing[0]
            # Merge tags: keep existing tags when caller didn't provide any
            import json as _j
            if tags_provided:
                existing_tags = _j.loads(existing[2] or "[]") if existing[2] else []
                merged_tags = list(dict.fromkeys(existing_tags + tags))
            else:
                merged_tags = _j.loads(existing[2] or "[]") if existing[2] else []
            update_note(
                note_path=existing_path,
                title=title,
                body=body,
                tags=merged_tags,
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

        try:
            rel_path = store_path(path.resolve())
        except ValueError:
            rel_path = str(path)
        return {
            "status": "created",
            "path": rel_path,
            "title": title,
            "domain": hostname,
            "message": f"Saved: '{title}' ({hostname}) → {rel_path}",
        }
    finally:
        conn.close()


@mcp.tool()
def sb_read(path: str) -> dict:
    """Read a note by absolute path."""
    rp = _resolve(path)
    content = rp.absolute.read_text(encoding="utf-8")
    conn = get_connection()
    pii_flag = False
    try:
        row = conn.execute(
            "SELECT sensitivity FROM notes WHERE path=?", (rp.relative,)
        ).fetchone()
    finally:
        conn.close()
    if row and row[0] == "pii":
        # MCP-05: PII content routed through Ollama adapter before returning to caller.
        adapter = get_adapter("pii", CONFIG_PATH)
        content = adapter.summarize(content)
        pii_flag = True
    try:
        _conn = get_connection()
        touch_note_access(_conn, rp.relative)
        _conn.close()
    except Exception:
        pass
    _log_mcp_audit("mcp_read", path)
    return {"content": content, "path": rp.relative, "pii": pii_flag}


@mcp.tool()
def sb_edit(path: str, body: str, importance: str | None = None) -> dict:
    """Edit an existing note's body. Writes atomically. Optionally updates importance."""
    import frontmatter as _fm
    p = _safe_path(path)
    if len(body) > _MAX_BODY_LEN:
        raise ValueError(f"BODY_TOO_LARGE: body exceeds {_MAX_BODY_LEN} characters.")
    if not p.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path!r} does not exist.")
    if importance is not None and importance not in ("low", "medium", "high"):
        raise ValueError("importance must be low, medium, or high")
    # Load existing frontmatter, update body, write atomically via engine helper
    post = _fm.load(str(p))
    post.content = body
    if importance is not None:
        post["importance"] = importance
    conn = get_connection()
    try:
        write_note_atomic(p, post, conn, update=True)
    finally:
        conn.close()
    _log_mcp_audit("mcp_edit", path)
    return {"status": "edited", "path": str(p)}


@mcp.tool()
def sb_rename(path: str, title: str) -> dict:
    """Rename a note's title.

    For person notes, also renames the file (slug derived from new title) and
    cascades the path change across all relationships, backlinks, attachments,
    tags, people, action items, and embeddings. Wiki-link text in other notes
    is rewritten to reference the new path.

    For all other note types, only the title field is updated (frontmatter +
    DB) — the filename is unchanged so all connections remain intact.

    Args:
        path: Relative or absolute path to the note (e.g. "person/john-smith.md").
        title: New title string (must not be blank).

    Returns:
        {
            "new_path": str,           # absolute path of the (possibly renamed) file
            "renamed_file": bool,      # True if the file was physically renamed
            "wiki_links_updated": int  # notes whose body was rewritten
        }
    """
    from engine.rename import rename_note
    p = _safe_path(path)
    if not p.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path!r}")
    title = title.strip()
    if not title:
        raise ValueError("TITLE_EMPTY: title must not be blank")
    conn = get_connection()
    try:
        result = rename_note(p, title, BRAIN_ROOT, conn)
        _log_mcp_audit("mcp_rename", path)
        return result
    finally:
        conn.close()


@mcp.tool()
def sb_recap(name: str | None = None, days: int | None = None) -> str:
    """Get session recap or cross-context synthesis for a person/project name."""
    import engine.mcp_server as _self
    if name is None and _detect_git_context is not None:
        name = _detect_git_context()
    if name is None:
        # Weekly session recap
        conn = get_connection()
        try:
            from engine.intelligence import generate_recap_on_demand
            result = generate_recap_on_demand(conn, window_days=days)
            _log_mcp_audit("mcp_recap", "session")
            return result or "No recent activity to recap."
        finally:
            conn.close()

    def _do_recap():
        conn = _self.get_connection()
        try:
            # Prepend overdue actions if any exist
            overdue = get_overdue_actions(conn)
            overdue_section = ""
            if overdue:
                lines = [f"- {a['text']} (due {a['due_date']})" for a in overdue[:10]]
                overdue_section = "**Overdue action items:**\n" + "\n".join(lines) + "\n\n"
            recap = recap_entity(name, conn)
            return (overdue_section + recap) if recap else overdue_section or None
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
    rp = _resolve(path)
    conn = get_connection()
    try:
        results = find_similar(rp.relative, conn)
    finally:
        conn.close()
    _log_mcp_audit("mcp_connections", path)
    return results


@mcp.tool()
def sb_actions(done: bool = False, page: int = 1, limit: int = 50) -> dict:
    """List action items. done=True lists completed items."""
    page = max(1, page)
    limit = min(limit, 200)
    offset = (page - 1) * limit
    conn = get_connection()
    try:
        all_results = list_actions(conn, done=done)
    finally:
        conn.close()
    total = len(all_results)
    results = all_results[offset:offset + limit]
    total_pages = math.ceil(total / limit) if limit else 1
    _log_mcp_audit("mcp_actions", "")
    return {"actions": results, "total": total, "page": page, "total_pages": total_pages}


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
def sb_files(subfolder: str | None = None, page: int = 1, limit: int = 50) -> dict:
    """List binary files in the brain, optionally filtered by subfolder."""
    files_dir = BRAIN_ROOT / "files"
    if not files_dir.exists():
        raise ValueError(f"FILES_DIR_NOT_FOUND: {files_dir} does not exist.")
    page = max(1, page)
    limit = min(limit, 200)
    offset = (page - 1) * limit
    if subfolder:
        search_root = (files_dir / subfolder).resolve()
        if not search_root.is_relative_to(files_dir.resolve()):
            raise ValueError("INVALID_SUBFOLDER: path traversal detected")
    else:
        search_root = files_dir
    all_files = []
    for f in sorted(search_root.rglob("*")):
        if f.is_file():
            rel = f.relative_to(files_dir)
            all_files.append({
                "name": f.name,
                "path": str(f),
                "subfolder": str(rel.parent) if rel.parent != Path(".") else "",
            })
    total = len(all_files)
    results = all_files[offset:offset + limit]
    total_pages = math.ceil(total / limit) if limit else 1
    _log_mcp_audit("mcp_files", str(files_dir))
    return {"files": results, "total": total, "page": page, "total_pages": total_pages}


@mcp.tool()
def sb_forget(slug: str, confirm_token: str = "") -> dict:
    """Forget all data for a person. Call once to get token; call again with token within 60s."""
    if not confirm_token:
        tok = _issue_token()
        # Build impact preview for the confirmation message
        from engine.delete import get_delete_impact
        from engine.paths import BRAIN_ROOT as _br, store_path
        _person_paths = [
            str(_br / "person" / f"{slug}.md"),
            str(_br / "people" / f"{slug}.md"),
        ]
        conn = get_connection()
        try:
            _impact_parts = []
            for _pp in _person_paths:
                try:
                    _ps = store_path(_pp)
                    _imp = get_delete_impact(_ps, conn)
                    if any(_imp.values()):
                        _impact_parts.append(
                            f"{_imp['action_items']} action items, "
                            f"{_imp['relationships']} relationships, "
                            f"mentioned in {_imp['appears_in_people_of']} notes"
                        )
                        break
                except Exception:
                    logger.debug("action_items insert skipped", exc_info=True)
        finally:
            conn.close()
        _impact_str = f" Impact: {_impact_parts[0]}." if _impact_parts else ""
        return {
            "status": "pending",
            "confirm_token": tok,
            "message": (
                f"Call sb_forget again with confirm_token='{tok}' within 60 seconds to execute."
                f"{_impact_str}"
            ),
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
    """Segment freeform text into typed notes and save them atomically.

    Multi-pass decomposition (engine.passes) splits the blob on structural markers
    (headings, ---, date stamps) and name-cluster shifts.  Each segment is classified,
    PII-scanned, and saved immediately — no confirm round-trip required.

    Co-captured notes are linked via 'co-captured' relationships and share a
    capture_session UUID so they can be retrieved as a group. Notes captured within
    15 minutes before this call are also auto-linked as co-captured.

    The returned capture_session UUID can be reused as session_id in subsequent
    sb_capture calls to continue grouping notes from the same conversation thread.

    Args:
        content: Freeform text to classify, segment, and save.

    Returns:
        {"status": "created", "notes": [...], "capture_session": str, "count": int,
         "recent_context": [...], "nudge": str (if linked with prior captures)}
        Each note dict contains: title, type, path, sensitivity, links, entities.
    """
    import datetime as _dt
    import itertools
    import pathlib as _pathlib
    import re as _re
    import uuid

    import frontmatter as _frontmatter

    from engine.segmenter import dedup_segment
    from engine.passes import decompose, CONFIDENCE_THRESHOLD
    from engine.smart_classifier import classify_smart

    _ensure_ready()

    if not content or not content.strip():
        return {
            "status": "created",
            "notes": [],
            "capture_session": str(uuid.uuid4()),
            "count": 0,
            "ambiguous_segments": [],
            "dormant_notes": [],
            "pending_review": [],
        }

    capture_session = str(uuid.uuid4())

    conn = get_connection()
    # decompose() runs Pass 1-5 including entity resolution (Pass 5) when conn+brain_root provided
    results = decompose(content, conn=conn, brain_root=BRAIN_ROOT)

    saved_notes: list[dict] = []
    ambiguous_segments: list[dict] = []
    pending_review: list[dict] = []
    stub_paths_created: dict[str, str] = {}  # name → path of created stub

    try:
        for result in results:
            title = result.primary_title
            note_type = result.primary_type
            confidence = result.confidence
            body = result.primary_body
            entities = result.entities

            # Resolved links from Pass 5 existing_people
            resolved_links = [e["path"] for e in result.existing_people if e.get("path")]

            # Link notes from Pass 2 (saved first per D-04)
            for link in result.link_notes:
                try:
                    _link_path = capture_note(
                        note_type="link",
                        title=link.title,
                        body=link.body,
                        tags=[],
                        people=[],
                        content_sensitivity="public",
                        brain_root=BRAIN_ROOT,
                        conn=conn,
                        url=link.url,
                    )
                    resolved_links.append(str(_link_path))
                    saved_notes.append({
                        "title": link.title,
                        "type": "link",
                        "path": str(_link_path),
                        "sensitivity": "public",
                        "links": [],
                        "entities": {},
                        "capture_session": capture_session,
                    })
                except Exception:
                    logger.debug("non-fatal operation skipped", exc_info=True)

            # Person stubs from Pass 5 (per D-12)
            for stub in result.person_stubs:
                stub_name = stub["name"]
                if stub_name in stub_paths_created:
                    resolved_links.append(stub_paths_created[stub_name])
                    continue
                try:
                    _stub_path = capture_note(
                        note_type=stub["type"],
                        title=stub_name,
                        body="",
                        tags=[],
                        people=[],
                        content_sensitivity="public",
                        brain_root=BRAIN_ROOT,
                        conn=conn,
                    )
                    stub_paths_created[stub_name] = str(_stub_path)
                    resolved_links.append(str(_stub_path))
                except Exception:
                    logger.debug("person stub creation skipped", exc_info=True)

            # Low-confidence type → ask caller instead of auto-saving
            if confidence < CONFIDENCE_THRESHOLD:
                pending_review.append({
                    "title": title,
                    "body": body,
                    "suggested_type": note_type,
                    "confidence": round(confidence, 2),
                    "people": entities.get("people", []),
                })
                continue

            sensitivity, _reason = classify_smart(body)
            # Merge resolved person paths with raw entity names (paths first, dedup)
            people = list(dict.fromkeys(resolved_links + entities.get("people", [])))
            from engine.typeclassifier import classify_importance as _classify_importance
            seg_importance = _classify_importance(title, body)

            dedup_result = dedup_segment(title, body, conn, BRAIN_ROOT)
            action = dedup_result["action"]

            if action == "ambiguous":
                ambiguous_segments.append({
                    "title": title,
                    "type": note_type,
                    "options": dedup_result.get("options", []),
                })
                continue

            elif action == "update_existing":
                existing_path = dedup_result["path"]
                existing_body = dedup_result["existing_body"]
                changelog_hash = dedup_result.get("changelog_hash", "")
                _now = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
                updated_body = (
                    f"{body}\n\n"
                    f"## Changelog\n"
                    f"Updated: {_now} — superseded previous version (hash: {changelog_hash})\n\n"
                    f"### Previous content\n{existing_body}"
                )
                try:
                    row = conn.execute(
                        "SELECT type, title, tags, people, content_sensitivity FROM notes WHERE path=?",
                        (existing_path,),
                    ).fetchone()
                    if row:
                        existing_post = _frontmatter.Post(updated_body)
                        existing_post["type"] = row[0]
                        existing_post["title"] = row[1]
                        existing_post["tags"] = _json_list(row[2])
                        existing_post["people"] = _json_list(row[3])
                        existing_post["content_sensitivity"] = row[4] or "public"
                        existing_post["date"] = _dt.date.today().isoformat()
                        existing_post["created_at"] = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
                        existing_post["updated_at"] = _now
                        write_note_atomic(
                            target=BRAIN_ROOT / existing_path,
                            post=existing_post,
                            conn=conn,
                            update=True,
                        )
                        saved_notes.append({
                            "title": title,
                            "type": note_type,
                            "path": existing_path,
                            "sensitivity": sensitivity,
                            "links": resolved_links,
                            "entities": entities,
                            "capture_session": capture_session,
                            "dedup_action": "updated_existing",
                        })
                        continue
                except Exception:
                    logger.debug("dedup check skipped", exc_info=True)

            elif action == "save_complementary":
                similar_path = dedup_result.get("similar_path", "")
                note_path = capture_note(
                    note_type=note_type,
                    title=title,
                    body=body,
                    tags=[],
                    people=people,
                    content_sensitivity=sensitivity,
                    brain_root=BRAIN_ROOT,
                    conn=conn,
                    importance=seg_importance,
                )
                if similar_path:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                            (store_path(note_path.resolve()), similar_path, "similar"),
                        )
                    except Exception:
                        logger.debug("relationship insert skipped", exc_info=True)
                saved_notes.append({
                    "title": title,
                    "type": note_type,
                    "path": str(note_path),
                    "sensitivity": sensitivity,
                    "links": resolved_links,
                    "entities": entities,
                    "capture_session": capture_session,
                    "dedup_action": "saved_complementary",
                    "relationships": [{"type": "similar", "path": similar_path}] if similar_path else [],
                })
                # Keyword action items (per D-08)
                try:
                    _ai_db_path = store_path(note_path.resolve())
                except (ValueError, Exception):
                    _ai_db_path = str(note_path)
                for _ai in result.action_items:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO action_items"
                            " (note_path, text, created_at)"
                            " VALUES (?, ?, datetime('now'))",
                            (_ai_db_path, _ai.text),
                        )
                    except Exception:
                        logger.debug("action_items insert skipped", exc_info=True)
                continue

            # Default: save_new
            note_path = capture_note(
                note_type=note_type,
                title=title,
                body=body,
                tags=[],
                people=people,
                content_sensitivity=sensitivity,
                brain_root=BRAIN_ROOT,
                conn=conn,
                importance=seg_importance,
            )

            # Keyword action items (per D-08)
            try:
                _ai_db_path = store_path(note_path.resolve())
            except (ValueError, Exception):
                _ai_db_path = str(note_path)
            for _ai in result.action_items:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO action_items"
                        " (note_path, item_text, status, created_at)"
                        " VALUES (?, ?, 'open', datetime('now'))",
                        (_ai_db_path, _ai.text),
                    )
                except Exception:
                    logger.debug("action_items insert skipped", exc_info=True)

            saved_notes.append({
                "title": title,
                "type": note_type,
                "path": str(note_path),
                "sensitivity": sensitivity,
                "links": resolved_links,
                "entities": entities,
                "capture_session": capture_session,
            })

        # Create co-captured relationships between all saved notes
        # Normalize to relative paths to satisfy FK constraint on notes.path
        _norm_paths = []
        for n in saved_notes:
            try:
                _norm_paths.append(store_path(Path(n["path"]).resolve()))
            except Exception:
                _norm_paths.append(n["path"])
        for src_path, tgt_path in itertools.combinations(_norm_paths, 2):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                    (src_path, tgt_path, "co-captured"),
                )
            except Exception:
                logger.debug("relationship insert skipped", exc_info=True)

        # Infer cross-links: meeting + person segments → add person slugs to meeting links
        if len(saved_notes) > 1:
            person_paths = [n["path"] for n in saved_notes if n["type"] in PERSON_TYPES]
            for note in saved_notes:
                if note["type"] == "meeting" and person_paths:
                    note["links"] = list(dict.fromkeys(note.get("links", []) + person_paths))

        conn.commit()

        # Dormant resurfacing — use first saved note path, best-effort
        dormant_notes: list[dict] = []
        if saved_notes:
            try:
                _first_path = saved_notes[0]["path"]
                try:
                    _first_path = store_path(Path(_first_path).resolve())
                except (ValueError, Exception):
                    logger.debug("non-fatal operation skipped", exc_info=True)
                dormant_notes = find_dormant_related(_first_path, conn)
            except Exception:
                logger.debug("dormant resurfacing skipped", exc_info=True)

        # Phase 56: find temporal neighbors OUTSIDE the batch for nudges
        recent_context: list[dict] = []
        nudge = ""
        if saved_notes:
            batch_paths = set(_norm_paths)
            import datetime as _dt
            _now = _dt.datetime.now(_dt.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ")
            try:
                ext_neighbors = find_temporal_neighbors(conn, _now, exclude_path=_norm_paths[0] if _norm_paths else None)
                ext_neighbors = [n for n in ext_neighbors if n["path"] not in batch_paths]
                recent_context = [
                    {"path": n["path"], "title": n["title"], "type": n["type"],
                     "minutes_ago": max(1, n["delta_seconds"] // 60)}
                    for n in ext_neighbors
                ]
                # Create co-captured links with external neighbors
                for n in ext_neighbors:
                    for bp in _norm_paths:
                        try:
                            conn.execute(
                                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                                (bp, n["path"], "co-captured"),
                            )
                            conn.execute(
                                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                                (n["path"], bp, "co-captured"),
                            )
                        except Exception:
                            logger.debug("co-captured relationship insert skipped", exc_info=True)
                if ext_neighbors:
                    conn.commit()
                    nudge = f"Also linked with {len(ext_neighbors)} note(s) captured earlier in this session."
            except Exception:
                logger.debug("temporal neighbor linking skipped", exc_info=True)

    finally:
        conn.close()

    result = {
        "status": "created",
        "notes": saved_notes,
        "capture_session": capture_session,
        "count": len(saved_notes),
        "dormant_notes": dormant_notes,
        "ambiguous_segments": ambiguous_segments,
        "pending_review": pending_review,
        "recent_context": recent_context,
    }
    if nudge:
        result["nudge"] = nudge
    return result



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

    if action not in ("add", "remove"):
        raise ValueError(f"INVALID_ACTION: action must be 'add' or 'remove', got {action!r}")

    rp = _resolve(path)
    if not rp.absolute.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path!r} does not exist.")

    conn = get_connection()
    try:
        if action == "remove":
            row = conn.execute("SELECT tags FROM notes WHERE path=?", (rp.relative,)).fetchone()
            current_tags = _json_list(row[0] if row else None)
            new_tags = [t for t in current_tags if t.lower() != tag.lower()]
            final_tag = tag
            _save_tags(rp.absolute, new_tags, rp.relative, conn)
            conn.commit()
            _log_mcp_audit("mcp_tag_remove", rp.relative)
            return {"path": rp.relative, "action": action, "tag": final_tag, "tags": new_tags}

        # "add" path -- gather all existing tags from DB
        rows = conn.execute(
            "SELECT DISTINCT j.value FROM notes, json_each(notes.tags) AS j WHERE notes.tags IS NOT NULL"
        ).fetchall()
        all_existing = [r[0] for r in rows if r[0]]

        matches = difflib.get_close_matches(tag, all_existing, n=1, cutoff=0.8)

        if matches:
            # Fuzzy match found -- use existing tag immediately, no confirm needed
            final_tag = matches[0]
            row = conn.execute("SELECT tags FROM notes WHERE path=?", (rp.relative,)).fetchone()
            current_tags = _json_list(row[0] if row else None)
            new_tags = list(dict.fromkeys(current_tags + [final_tag]))
            _save_tags(rp.absolute, new_tags, rp.relative, conn)
            conn.commit()
            _log_mcp_audit("mcp_tag_add", rp.relative)
            return {
                "path": rp.relative, "action": action, "tag": final_tag, "tags": new_tags,
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
        row = conn.execute("SELECT tags FROM notes WHERE path=?", (rp.relative,)).fetchone()
        current_tags = _json_list(row[0] if row else None)
        new_tags = list(dict.fromkeys(current_tags + [final_tag]))
        _save_tags(rp.absolute, new_tags, rp.relative, conn)
        conn.commit()
        _log_mcp_audit("mcp_tag_add", rp.relative)
        return {"path": rp.relative, "action": action, "tag": final_tag, "tags": new_tags}
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
def sb_link(source_path: str, target_path: str, rel_type: str = "link", bidirectional: bool = False) -> dict:
    """Create a relationship between two notes. DB-only — does not edit note bodies.

    rel_type: arbitrary string label, default 'link'.
    Common values: 'link', 'references', 'similar', 'part-of'.
    bidirectional: when True, inserts both A->B and B->A rows.
    Idempotent — calling with the same (source, target, rel_type) twice inserts only one row.
    """
    # Normalize to relative DB paths for consistent lookups
    try:
        src = store_path(Path(source_path).resolve()) if Path(source_path).is_absolute() else source_path
    except ValueError:
        src = source_path
    try:
        tgt = store_path(Path(target_path).resolve()) if Path(target_path).is_absolute() else target_path
    except ValueError:
        tgt = target_path

    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
            (src, tgt, rel_type),
        )
        if bidirectional:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
                (tgt, src, rel_type),
            )
        conn.commit()
        return {"linked": True, "source": src, "target": tgt, "rel_type": rel_type, "bidirectional": bidirectional}
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
def sb_traverse(start_path: str, max_depth: int = 2, rel_types: str | None = None) -> dict:
    """Explore associative connections from a starting note.

    Follow relationship chains up to N hops to discover indirect connections
    between notes, people, and projects. Use when you want to understand how
    topics are connected beyond direct links.

    Args:
        start_path: Path of the note to start traversal from.
        max_depth: Maximum hops to follow (1-3, default 2).
        rel_types: Comma-separated relationship types to follow (e.g. "wiki-link,connection").
                   If omitted, follows all types.

    Returns:
        {nodes: [{path, title, note_type, depth, activation}],
         edges: [{source, target, type, strength}]}
    """
    parsed_types = [t.strip() for t in rel_types.split(",") if t.strip()] if rel_types else None
    conn = get_connection()
    try:
        result = traverse_graph(conn, start_path, max_depth=max_depth, rel_types=parsed_types)
        log_audit(conn, "mcp_traverse", start_path, f"depth={max_depth}")
        return result
    finally:
        conn.close()


@mcp.tool()
def sb_surface(context: str, max_results: int = 5, include_graph: bool = True) -> dict:
    """Proactively surface notes relevant to the current conversation context.

    Call this when: starting work on a topic, the user mentions a person/project
    you haven't looked up, or you sense historical context would help.
    Do NOT call this on every message — use judgment.

    Args:
        context: Free-text describing what's being discussed (you provide this).
        max_results: Maximum suggestions to return (default 5).
        include_graph: If True, follow 1-hop graph links from top results to find
                       associatively connected notes (requires Phase 52).

    Returns:
        {suggestions: [{path, title, snippet, relevance_score, reason}],
         graph_additions: [{path, title, note_type, via}]}
    """
    conn = get_connection()
    try:
        suggestions = surface_relevant(conn, context, max_results=max_results)

        graph_additions: list[dict] = []
        if include_graph and suggestions:
            try:
                seen_paths = {s["path"] for s in suggestions}
                # Follow 1-hop graph links from top 2 results
                for s in suggestions[:2]:
                    graph_result = traverse_graph(conn, s["path"], max_depth=1)
                    for node in graph_result["nodes"]:
                        if node["path"] not in seen_paths and node["note_type"] in ("person", "project"):
                            graph_additions.append({
                                "path": node["path"],
                                "title": node["title"],
                                "note_type": node["note_type"],
                                "via": s["title"],
                            })
                            seen_paths.add(node["path"])
            except Exception:
                pass  # graph enrichment is best-effort

        log_audit(conn, "mcp_surface", context[:200])
        return {"suggestions": suggestions, "graph_additions": graph_additions}
    finally:
        conn.close()


@mcp.tool()
def sb_insights(days: int = 7) -> dict:
    """Surface recent insights from the brain's nightly synthesis process.

    Shows consolidated knowledge, patterns, and contradictions detected across
    related notes. Call this for a high-level view of recent activity patterns.

    Args:
        days: How many days back to look for synthesis notes (default 7).

    Returns:
        {syntheses: [{path, title, summary, source_notes, tags, people}],
         contradictions: [{notes, issue}],
         period_days: int}
    """
    import json as _json
    conn = get_connection()
    try:
        cutoff = (
            datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            - datetime.timedelta(days=days)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        rows = conn.execute(
            "SELECT path, title, body, tags, people FROM notes "
            "WHERE type = 'synthesis' AND created_at >= ? "
            "ORDER BY created_at DESC",
            (cutoff,),
        ).fetchall()

        syntheses = []
        for path, title, body, tags_raw, people_raw in rows:
            tags = _json.loads(tags_raw) if tags_raw else []
            people = _json.loads(people_raw) if people_raw else []
            # Extract source_notes from frontmatter (stored in body via frontmatter lib)
            summary = (body or "")[:500]
            syntheses.append({
                "path": path,
                "title": title,
                "summary": summary,
                "tags": tags,
                "people": people,
            })

        # Simple contradiction detection: find notes in same cluster with different dates
        # for the same tag (heuristic — different deadline mentions)
        contradictions: list[dict] = []
        try:
            from engine.intelligence import cluster_recent_notes
            clusters = cluster_recent_notes(conn, window_days=days)
            for cluster in clusters:
                # Check for date conflicts in note bodies
                dates_by_note: dict[str, list[str]] = {}
                import re
                for note_path in cluster["notes"]:
                    row = conn.execute("SELECT body FROM notes WHERE path = ?", (note_path,)).fetchone()
                    if row and row[0]:
                        found_dates = re.findall(r"\d{4}-\d{2}-\d{2}", row[0])
                        if found_dates:
                            dates_by_note[note_path] = found_dates
                if len(dates_by_note) >= 2:
                    all_dates = set()
                    for d_list in dates_by_note.values():
                        all_dates.update(d_list)
                    if len(all_dates) > 1:
                        contradictions.append({
                            "notes": list(dates_by_note.keys()),
                            "issue": f"Different dates mentioned across cluster '{cluster['topic']}': {sorted(all_dates)[:5]}",
                        })
        except Exception:
            pass  # contradiction detection is best-effort

        if not syntheses:
            return {
                "syntheses": [],
                "contradictions": contradictions,
                "period_days": days,
                "message": "No synthesis notes yet. They are generated nightly from clusters of 3+ related notes.",
            }

        log_audit(conn, "mcp_insights", f"days={days}")
        return {"syntheses": syntheses, "contradictions": contradictions, "period_days": days}
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
                f"SELECT title, body, entities FROM notes WHERE path=? AND type IN ({PERSON_TYPES_PH})",
                (person_path, *PERSON_TYPES),
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT path, title, body, entities FROM notes "
                f"WHERE LOWER(title)=LOWER(?) AND type IN ({PERSON_TYPES_PH}) LIMIT 1",
                (name_or_path, *PERSON_TYPES),
            ).fetchone()
            if row is None:
                return {"found": False, "error": f"Person not found: {name_or_path!r}"}
            person_path = row["path"]

        if row is None:
            return {"found": False, "error": f"Person not found: {name_or_path!r}"}

        person_title = row["title"]

        # 2+3. Meetings and mentions — use note_people junction table if populated (fast path),
        # fall back to json_each scans if note_people has no entries for this person.
        np_count = conn.execute(
            "SELECT COUNT(*) FROM note_people WHERE person=? OR person LIKE ?",
            (person_path, f"%{person_title}%"),
        ).fetchone()[0]

        if np_count > 0:
            # Fast path: indexed junction table — single query, split by type in Python
            all_note_rows = conn.execute(
                """
                SELECT DISTINCT n.path, n.title, n.type, n.created_at
                FROM note_people np
                JOIN notes n ON np.note_path = n.path
                WHERE np.person = ? OR np.person LIKE ?
                ORDER BY n.created_at DESC
                LIMIT 20
                """,
                (person_path, f"%{person_title}%"),
            ).fetchall()
            meeting_rows = [r for r in all_note_rows if r["type"] == "meeting"]
            mention_rows = [r for r in all_note_rows if r["type"] not in (*PERSON_TYPES, "meeting")]
        else:
            # Fallback: json_each scan (handles fresh installs where note_people is not yet populated)
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
            mention_rows = conn.execute(
                """
                SELECT DISTINCT n.path, n.title, n.created_at
                FROM notes n, json_each(COALESCE(n.people, '[]')) pe
                WHERE (pe.value = ? OR pe.value LIKE ?)
                  AND n.type NOT IN ('person', 'meeting')
                ORDER BY n.created_at DESC
                """,
                (person_path, f"%{person_title}%"),
            ).fetchall()

        meetings = [
            {"path": r["path"], "title": r["title"], "meeting_date": (r["created_at"] or "")[:10]}
            for r in meeting_rows
        ]
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

        try:
            touch_note_access(conn, person_path)
        except Exception:
            pass
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

        # 6. 2nd-degree connections via graph traversal
        try:
            graph = traverse_graph(conn, person_path, max_depth=2)
            connected_people = []
            for node in graph["nodes"]:
                if node["path"] == person_path:
                    continue
                if node.get("note_type") not in PERSON_TYPES:
                    continue
                # Find the intermediate note connecting them
                via = None
                for edge in graph["edges"]:
                    if node["path"] in (edge["source"], edge["target"]):
                        other = edge["source"] if edge["target"] == node["path"] else edge["target"]
                        if other != person_path:
                            via_row = conn.execute(
                                "SELECT title FROM notes WHERE path = ?", (other,)
                            ).fetchone()
                            via = via_row[0] if via_row else other
                            break
                connected_people.append({
                    "path": node["path"],
                    "title": node["title"],
                    "via": via,
                    "depth": node["depth"],
                })
            result["connected_people"] = connected_people
        except Exception:
            result["connected_people"] = []

        return result
    finally:
        conn.close()



@mcp.tool()
def sb_list_persons() -> dict:
    """List all person notes with relationship metrics: open actions, org, last interaction, mention count.

    Returns:
        {people: [{path, title, open_actions, org, last_interaction, total_meetings, total_mentions}]}
        Ordered alphabetically by title.
    """
    from engine.people import list_people_with_metrics
    conn = get_connection()
    try:
        people = list_people_with_metrics(conn)
        # Rename mention_count → total_mentions for MCP backward compat
        for p in people:
            p["total_mentions"] = p.pop("mention_count", 0)
        return {"people": people}
    finally:
        conn.close()


@mcp.tool()
def sb_create_person(name: str, role: str = "") -> dict:
    """Create a new person note in the brain.

    Args:
        name: Person's name (required)
        role: Person's role or title (optional)

    Returns:
        dict with path and title of created note
    """
    _ensure_ready()
    if not name.strip():
        return {"error": "name is required"}
    body = f"Role: {role}" if role.strip() else ""
    from engine.capture import capture_note
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
        result_path = capture_note(
            note_type="person",
            title=name.strip(),
            body=body,
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=BRAIN_ROOT,
            conn=conn,
        )
    finally:
        conn.close()
    return {"path": str(result_path), "title": name.strip()}


@mcp.tool()
def sb_merge_duplicates(threshold: float = 0.92, limit: int = 20) -> dict:
    """Return near-duplicate note pairs above similarity threshold.

    Use this to discover duplicate notes before merging with sb_merge_confirm.
    threshold: cosine similarity cutoff (0.92 = very similar). limit: max pairs to return.
    """
    conn = get_connection()
    try:
        from engine.brain_health import get_duplicate_candidates
        pairs = get_duplicate_candidates(conn, threshold=threshold)[:limit]
        return {"pairs": pairs, "count": len(pairs)}
    finally:
        conn.close()


@mcp.tool()
def sb_merge_confirm(keep_path: str, discard_path: str, confirm_token: str = "") -> dict:
    """Merge two duplicate notes. Requires confirm_token (two-step safety).

    Step 1: Call without confirm_token to get a token.
    Step 2: Call again with confirm_token within 60s to execute the merge.
    keep_path: note to keep (merge target). discard_path: note to delete after merge.
    """
    if not confirm_token:
        tok = _issue_token()
        return {
            "status": "pending",
            "confirm_token": tok,
            "message": (
                f"Will merge '{discard_path}' into '{keep_path}'. "
                f"Call again with confirm_token='{tok}' within 60s."
            ),
        }
    if not _consume_token(confirm_token):
        raise ValueError(
            "TOKEN_EXPIRED: confirm_token invalid or expired. "
            "Call sb_merge_confirm without a token to get a new one."
        )
    from engine.brain_health import merge_notes
    conn = get_connection()
    try:
        result = merge_notes(keep_path, discard_path, conn)
        return {"status": "merged", **result}
    finally:
        conn.close()


@mcp.tool()
def sb_find_stubs(word_limit: int = 50, similarity_threshold: float = 0.85) -> dict:
    """Return stub notes (< word_limit words) with similarity matches for merge-first workflow.

    Per D-05, D-06: stubs with a similar fuller note are routed as merge candidates (action=merge).
    Stubs with no similar notes are candidates for enrichment (action=enrich).
    word_limit: notes with fewer words than this are stubs (default 50).
    similarity_threshold: cosine similarity cutoff for merge candidate detection (default 0.85).
    """
    conn = get_connection()
    try:
        from engine.brain_health import get_stub_notes
        stubs = get_stub_notes(conn, word_limit=word_limit)
        enriched = []
        for stub in stubs:
            matches = []
            try:
                from engine.intelligence import find_similar
                from engine.paths import store_path
                path = stub["path"]
                try:
                    path = store_path(path)
                except (ValueError, Exception):
                    logger.debug("intelligence hook error", exc_info=True)
                similar = find_similar(path, conn, threshold=similarity_threshold, limit=3)
                matches = [m for m in similar if m["note_path"] != stub["path"]]
            except Exception:
                logger.debug("intelligence hook error", exc_info=True)
            enriched.append({
                **stub,
                "similar_notes": matches,
                "action": "merge" if matches else "enrich",
            })
        return {"stubs": enriched, "count": len(enriched)}
    finally:
        conn.close()


@mcp.tool()
def sb_cleanup_connections() -> dict:
    """Delete dangling relationships and flag bidirectional gaps.

    Per D-08, D-09: removes stale graph edges (dangling) and surfaces one-way links (gaps)
    for manual review. Returns counts for transparency.
    """
    conn = get_connection()
    try:
        from engine.brain_health import delete_dangling_relationships, get_bidirectional_gaps
        deleted = delete_dangling_relationships(conn)
        gaps = get_bidirectional_gaps(conn)
        return {
            "deleted_dangling": deleted,
            "bidirectional_gaps": gaps,
            "gap_count": len(gaps),
        }
    finally:
        conn.close()


@mcp.tool()
def sb_health_trend(days: int = 30) -> dict:
    """Return health snapshots as a time series for the last N days."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT snapped_at, score, total_notes, orphan_count, broken_count, duplicate_count, stub_count
            FROM health_snapshots
            WHERE snapped_at >= date('now', ?)
            ORDER BY snapped_at ASC
        """, (f"-{days} days",)).fetchall()
        snapshots = [
            {"snapped_at": r[0], "score": r[1], "total_notes": r[2],
             "orphan_count": r[3], "broken_count": r[4],
             "duplicate_count": r[5], "stub_count": r[6]}
            for r in rows
        ]
        return {"snapshots": snapshots, "count": len(snapshots), "days": days}
    finally:
        conn.close()


def main() -> None:
    mcp.run(transport="stdio")
