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

from engine.capture import build_post, capture_note, check_capture_dedup, log_audit, write_note_atomic
from engine.db import get_connection
from engine.digest import generate_digest
from engine.forget import forget_person
from engine.anonymize import anonymize_note
from engine.intelligence import find_similar, list_actions, recap_entity
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
        write_note_atomic(p, post, conn)
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


def main() -> None:
    mcp.run(transport="stdio")
