"""FTS5 BM25 full-text search with audit log."""
import datetime
import sqlite3


def _fts5_query(query: str) -> str:
    """Wrap a raw user query in FTS5 phrase quotes.

    FTS5 treats hyphens as subtraction operators in bare queries (e.g. "alice-smith"
    parses as "alice" minus column "smith", raising OperationalError).  Wrapping the
    whole query in double-quotes makes it a phrase search, which is the correct
    semantics for name/slug lookups.  Internal double-quotes are escaped by doubling.
    """
    escaped = query.replace('"', '""')
    return f'"{escaped}"'


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
        query: Raw search query (automatically phrase-quoted for FTS5 safety).
        note_type: If provided, restrict results to notes of this type.
        limit: Maximum number of results to return.

    Returns:
        List of result dicts, empty list when no notes match.
    """
    fts_query = _fts5_query(query)
    if note_type is None:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
        """
        rows = conn.execute(sql, (fts_query, limit)).fetchall()
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
        rows = conn.execute(sql, (fts_query, note_type, limit)).fetchall()

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


def main() -> None:
    """CLI entry point for sb-search."""
    import argparse
    from engine.db import get_connection, init_schema

    parser = argparse.ArgumentParser(description="Search the second brain")
    parser.add_argument("query")
    parser.add_argument("--type", dest="note_type", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    conn = get_connection()
    init_schema(conn)
    results = search_notes(conn, args.query, note_type=args.note_type, limit=args.limit)

    if not results:
        print("No results found.")
        conn.close()
        return
    for r in results:
        print(f"{r['path']} | {r['title']} | {r['score']:.4f}")

    # Phase 15: best-effort stale nudge — never blocks search
    try:
        from engine.intelligence import check_stale_nudge
        check_stale_nudge(conn)
    except Exception:
        pass

    conn.close()
