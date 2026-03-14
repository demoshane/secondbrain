"""FTS5 BM25 full-text search with audit log."""
import datetime
import sqlite3


def search_notes(
    conn: sqlite3.Connection,
    query: str,
    note_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search notes using FTS5 BM25 ranking.

    Returns dicts with keys: path, type, title, created_at, score (float, negative).
    Results ordered best-match first (most negative BM25 score = best match).
    Inserts one row into audit_log for every call.

    Args:
        conn: SQLite connection with schema already initialised.
        query: FTS5 MATCH query string.
        note_type: If provided, restrict results to notes of this type.
        limit: Maximum number of results to return.

    Returns:
        List of result dicts, empty list when no notes match.
    """
    if note_type is None:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
        """
        rows = conn.execute(sql, (query, limit)).fetchall()
    else:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
              AND n.type = ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
        """
        rows = conn.execute(sql, (query, note_type, limit)).fetchall()

    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        ("search", None, query, datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()

    return [
        {
            "path": row[0],
            "type": row[1],
            "title": row[2],
            "created_at": row[3],
            "score": row[4],
        }
        for row in rows
    ]
