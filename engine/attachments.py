"""Attachment persistence layer — save, list, and upload-suppress helpers.

Used by the POST /files/upload endpoint to record file uploads in the
attachments table and suppress spurious watchdog 'created' events for
files we intentionally wrote to disk.
"""
import threading

from engine.db import get_connection

# ---------------------------------------------------------------------------
# Upload-suppress set: prevents watchdog from double-firing on files we save
# ---------------------------------------------------------------------------

_upload_suppress: set[str] = set()
_upload_suppress_lock = threading.Lock()


def suppress_next_create(abs_path: str, window: float = 0.5) -> None:
    """Record abs_path so _fire() skips the next 'created' event within window seconds."""
    with _upload_suppress_lock:
        _upload_suppress.add(abs_path)
    threading.Timer(window, _clear_suppress, args=(abs_path,)).start()


def _clear_suppress(abs_path: str) -> None:
    with _upload_suppress_lock:
        _upload_suppress.discard(abs_path)


def is_upload_suppressed(abs_path: str) -> bool:
    """Return True if the path is currently in the upload-suppress window."""
    with _upload_suppress_lock:
        return abs_path in _upload_suppress


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def save_attachment(note_path: str, file_path: str, filename: str, size: int) -> dict:
    """Insert an attachment row and return the full row as a dict.

    Args:
        note_path: Relative or absolute path of the note this attachment belongs to.
        file_path: Absolute path where the file was saved on disk.
        filename:  Sanitised filename (after secure_filename).
        size:      File size in bytes.

    Returns:
        dict with keys: id, note_path, file_path, filename, size, uploaded_at.
    """
    conn = get_connection()
    conn.row_factory = None  # reset in case caller left it set
    try:
        cur = conn.execute(
            "INSERT INTO attachments (note_path, file_path, filename, size) VALUES (?, ?, ?, ?)",
            (note_path, file_path, filename, size),
        )
        conn.commit()
        fetch_cur = conn.execute(
            "SELECT id, note_path, file_path, filename, size, uploaded_at "
            "FROM attachments WHERE id=?",
            (cur.lastrowid,),
        )
        col_names = [d[0] for d in fetch_cur.description]
        row = fetch_cur.fetchone()
        return dict(zip(col_names, row))
    finally:
        conn.close()


def list_attachments(note_path: str) -> list[dict]:
    """Return all attachments for note_path, ordered by id ascending.

    Returns:
        List of dicts with keys: id, note_path, file_path, filename, size, uploaded_at.
    """
    conn = get_connection()
    conn.row_factory = None
    try:
        cur = conn.execute(
            "SELECT id, note_path, file_path, filename, size, uploaded_at "
            "FROM attachments WHERE note_path=? ORDER BY id",
            (note_path,),
        )
        col_names = [d[0] for d in cur.description]
        return [dict(zip(col_names, row)) for row in cur.fetchall()]
    finally:
        conn.close()
