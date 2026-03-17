"""FTS5 BM25 full-text search with audit log, plus semantic and hybrid RRF modes."""
import datetime
import math
import sqlite3


def _recency_multiplier(created_at_str: str, half_life_days: int = 30) -> float:
    """Return a score multiplier >= 1.0 based on note age.

    New notes get a small boost (~1.1); the boost decays exponentially with a
    configurable half-life (default 30 days).  At 180+ days the multiplier
    approaches 1.0 (no meaningful boost).

    Args:
        created_at_str: ISO-8601 timestamp string (trailing 'Z' is stripped).
        half_life_days: Days after which the boost halves. Default 30.

    Returns:
        Float >= 1.0. Falls back to 1.0 on any parse error.
    """
    try:
        created = datetime.datetime.fromisoformat(str(created_at_str).rstrip("Z"))
        age_days = (datetime.datetime.utcnow() - created).days
        boost = 0.1
        scale = half_life_days / math.log(2)
        return 1.0 + boost * math.exp(-age_days / scale)
    except Exception:
        return 1.0


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
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
            ORDER BY bm25(notes_fts, 10.0, 1.0)
            LIMIT ?
        """
        rows = conn.execute(sql, (fts_query, limit)).fetchall()
    else:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
              AND n.type = ?
            ORDER BY bm25(notes_fts, 10.0, 1.0)
            LIMIT ?
        """
        rows = conn.execute(sql, (fts_query, note_type, limit)).fetchall()

    conn.execute(
        "INSERT INTO audit_log (event_type, note_path, detail, created_at) VALUES (?, ?, ?, ?)",
        ("search", None, query, datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
    )
    conn.commit()

    results = [
        {
            "path": row[0],
            "type": row[1],
            "title": row[2],
            "created_at": row[3],
            "score": row[4],
        }
        for row in rows
    ]
    results = [
        {**r, "score": r["score"] * _recency_multiplier(r.get("created_at", ""))}
        for r in results
    ]
    return results


def _rrf_merge(
    bm25_results: list[dict],
    vec_results: list[dict],
    k: int = 60,
    limit: int = 20,
) -> list[dict]:
    """Merge two ranked lists via Reciprocal Rank Fusion.

    Works on rank positions (enumerate index), NOT raw scores.
    Higher RRF score = better merged rank.
    """
    scores: dict[str, float] = {}
    all_items: dict[str, dict] = {}
    for rank, item in enumerate(bm25_results):
        p = item["path"]
        scores[p] = scores.get(p, 0.0) + 1.0 / (k + rank + 1)
        all_items[p] = item
    for rank, item in enumerate(vec_results):
        p = item["path"]
        scores[p] = scores.get(p, 0.0) + 1.0 / (k + rank + 1)
        all_items[p] = item
    ranked = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)
    return [all_items[p] for p in ranked[:limit]]


def search_semantic(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Semantic vector search using sqlite-vec KNN.

    Embeds the query via embed_texts, then runs a cosine-distance KNN query
    against note_embeddings. Returns list[dict] with keys: path, title, type,
    created_at, score (1.0 - cosine_distance, higher = better match).

    Fallback behaviour:
    - If sqlite-vec fails to load: returns [].
    - If note_embeddings table is empty: prints a notification and returns [].
    - If >50 notes lack embeddings: prints a warning and searches what's indexed.
    """
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        return []

    count = conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
    if count == 0:
        print("Semantic unavailable. Run sb-reindex to enable.")
        return []

    missing = conn.execute(
        "SELECT COUNT(*) FROM notes n "
        "LEFT JOIN note_embeddings ne ON ne.note_path = n.path "
        "WHERE ne.note_path IS NULL"
    ).fetchone()[0]
    if missing > 50:
        print(
            f"{missing} notes missing embeddings. "
            "Run sb-reindex to enable full semantic search."
        )

    from engine.embeddings import embed_texts
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH

    cfg = load_config(CONFIG_PATH)
    provider = cfg.get("embeddings", {}).get("provider", "ollama")
    query_blob = embed_texts([query], provider=provider)[0]

    rows = conn.execute(
        """
        SELECT
            ne.note_path AS path,
            n.title,
            n.type,
            n.created_at,
            n.sensitivity,
            vec_distance_cosine(ne.embedding, ?) AS dist
        FROM note_embeddings ne
        JOIN notes n ON ne.note_path = n.path
        ORDER BY dist
        LIMIT ?
        """,
        (query_blob, limit),
    ).fetchall()

    return [
        {
            "path": row[0],
            "title": row[1],
            "type": row[2],
            "created_at": row[3],
            "score": 1.0 - row[5],
        }
        for row in rows
    ]


def search_hybrid(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Hybrid search: merges BM25 and vector results via Reciprocal Rank Fusion.

    Falls back to pure FTS5 results when:
    - sqlite-vec fails to load.
    - note_embeddings table is empty (prints a notification).
    - search_semantic raises an unexpected exception.
    """
    bm25 = search_notes(conn, query, limit=limit * 2)

    try:
        vec_results = search_semantic(conn, query, limit=limit * 2)
    except Exception:
        return bm25[:limit]

    if not vec_results:
        # search_semantic already printed a notification if relevant
        return bm25[:limit]

    return _rrf_merge(bm25, vec_results, k=60, limit=limit)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for sb-search."""
    import argparse
    from engine.db import get_connection, init_schema

    parser = argparse.ArgumentParser(description="Search the second brain")
    parser.add_argument("query")
    parser.add_argument("--type", dest="note_type", default=None)
    parser.add_argument("--limit", type=int, default=20)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--semantic", action="store_true", help="Pure vector search")
    mode_group.add_argument("--keyword", action="store_true", help="Pure BM25 keyword search")
    args = parser.parse_args(argv)

    conn = get_connection()
    init_schema(conn)

    if args.semantic:
        results = search_semantic(conn, args.query, limit=args.limit)
    elif args.keyword:
        results = search_notes(conn, args.query, note_type=args.note_type, limit=args.limit)
    else:
        results = search_hybrid(conn, args.query, limit=args.limit)

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
