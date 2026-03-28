"""FTS5 BM25 full-text search with audit log, plus semantic and hybrid RRF modes."""
import datetime
import json as _json
import logging
import math
import re
import sqlite3

logger = logging.getLogger(__name__)


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
    """Build an FTS5 query with per-token prefix matching.

    Each whitespace-separated token becomes a prefix term ("token"*), so partial
    words like "Verifi" match "Verification", "Verified", etc.  Multiple tokens
    are AND-joined, so "Eino Ki" matches notes containing words starting with
    both "Eino" and "Ki".  Internal double-quotes are escaped by doubling.
    """
    tokens = query.split()
    if not tokens:
        return '""'
    parts = [f'"{t.replace(chr(34), chr(34) + chr(34))}"*' for t in tokens]
    return " ".join(parts)


_QUESTION_STOP_WORDS = frozenset({
    "who", "what", "when", "where", "why", "how", "is", "are", "was", "were",
    "do", "does", "did", "tell", "me", "about", "know", "have", "i", "you",
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "and",
    "or", "that", "this", "it", "he", "she", "his", "her", "my", "any",
    "can", "could", "would", "should", "please", "give", "show", "list",
    "get", "find", "remember",
})


def _fts5_keyword_query(query: str) -> str:
    """Convert a natural-language question to an AND-joined FTS5 keyword search.

    Strips common question/stop words, then AND-joins the remaining meaningful
    tokens.  Falls back to a full phrase search if no meaningful tokens remain.
    """
    tokens = re.findall(r'\b\w+\b', query.lower())
    meaningful = [t for t in tokens if t not in _QUESTION_STOP_WORDS and len(t) > 1]
    if not meaningful:
        return _fts5_query(query)
    escaped = [f'"{t.replace(chr(34), chr(34) + chr(34))}"' for t in meaningful]
    return " AND ".join(escaped)


def search_notes(
    conn: sqlite3.Connection,
    query: str,
    note_type: str | None = None,
    limit: int = 20,
    natural_language: bool = False,
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
        natural_language: When True, strips question stop words and uses
            AND-joined keyword search instead of full-phrase matching.
            Use this for free-form questions (e.g. Ask Brain queries).

    Returns:
        List of result dicts, empty list when no notes match.
    """
    fts_query = _fts5_keyword_query(query) if natural_language else _fts5_query(query)
    if note_type is None:
        sql = """
            SELECT n.path, n.type, n.title, n.created_at, bm25(notes_fts, 10.0, 1.0) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.rowid = n.id
            WHERE notes_fts MATCH ?
              AND n.archived = 0
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
              AND n.archived = 0
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
            "excerpt": None,
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


def _enrich_with_excerpts(conn: sqlite3.Connection, results: list[dict], query: str) -> list[dict]:
    """Add excerpt field to each result from note_chunks table.

    For each result, finds the best-matching chunk by cosine similarity against
    the query embedding. Sets r["excerpt"] to the trimmed chunk text (max 300 chars),
    or None if no chunks exist or embeddings are unavailable.
    """
    try:
        from engine.embeddings import embed_texts
        query_blob = embed_texts([query])[0]
    except Exception:
        for r in results:
            r["excerpt"] = None
        return results

    import numpy as np
    query_vec = np.frombuffer(query_blob, dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)

    for r in results:
        chunks = conn.execute(
            "SELECT chunk_text, embedding FROM note_chunks WHERE note_path=?",
            (r["path"],)
        ).fetchall()
        if not chunks or not chunks[0][1]:
            r["excerpt"] = None
            continue
        best_text = None
        best_sim = -1.0
        for chunk_text, emb_blob in chunks:
            if not emb_blob:
                continue
            chunk_vec = np.frombuffer(emb_blob, dtype=np.float32)
            # Handle dimension mismatch gracefully
            if len(chunk_vec) != len(query_vec):
                continue
            dot = np.dot(query_vec, chunk_vec)
            norm = query_norm * np.linalg.norm(chunk_vec)
            sim = dot / (norm + 1e-9)
            if sim > best_sim:
                best_sim = sim
                best_text = chunk_text
        r["excerpt"] = best_text[:300] if best_text else None
    return results


def search_semantic(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
) -> list[dict]:
    """Semantic vector search using hnswlib ANN (with sqlite-vec fallback).

    Tries hnswlib ANN first (O(log n) at scale). Falls back to sqlite-vec KNN
    on any failure. Returns list[dict] with keys: path, title, type,
    created_at, score, excerpt (1.0 - cosine_distance, higher = better match).

    Fallback behaviour:
    - If hnswlib unavailable or ANN returns empty: falls back to sqlite-vec.
    - If sqlite-vec fails to load: returns [].
    - If note_embeddings table is empty: prints a notification and returns [].
    - If >50 notes lack embeddings: prints a warning and searches what's indexed.
    """
    # Try hnswlib ANN first (O(log n) at scale)
    try:
        from engine.ann_index import knn_query as _ann_knn
        from engine.embeddings import embed_texts
        query_blob = embed_texts([query])[0]
        ann_results = _ann_knn(query_blob, k=limit, conn=conn)
        if ann_results:
            results = []
            for note_path, distance in ann_results:
                row = conn.execute(
                    "SELECT path, type, title, created_at FROM notes WHERE path=?",
                    (note_path,)
                ).fetchone()
                if row:
                    score = 1.0 - distance  # cosine distance -> similarity
                    results.append({
                        "path": row[0], "type": row[1], "title": row[2],
                        "created_at": row[3], "score": score * _recency_multiplier(row[3]),
                    })
            if results:
                results = sorted(results, key=lambda r: r["score"], reverse=True)[:limit]
                return _enrich_with_excerpts(conn, results, query)
    except Exception as e:
        logger.warning("ANN search failed, falling back to sqlite-vec: %s", e)

    # Fallback: sqlite-vec KNN
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        return []

    count = conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
    if count == 0:
        logger.warning("Semantic unavailable. Run sb-reindex to enable.")
        return []

    missing = conn.execute(
        "SELECT COUNT(*) FROM notes n "
        "LEFT JOIN note_embeddings ne ON ne.note_path = n.path "
        "WHERE ne.note_path IS NULL"
    ).fetchone()[0]
    if missing > 50:
        logger.warning(
            "%d notes missing embeddings. Run sb-reindex to enable full semantic search.",
            missing,
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

    results = [
        {
            "path": row[0],
            "title": row[1],
            "type": row[2],
            "created_at": row[3],
            "score": 1.0 - row[5],
        }
        for row in rows
    ]
    return _enrich_with_excerpts(conn, results, query)


def search_hybrid(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    natural_language: bool = False,
) -> list[dict]:
    """Hybrid search: merges BM25 and vector results via Reciprocal Rank Fusion.

    Falls back to pure FTS5 results when:
    - sqlite-vec fails to load.
    - note_embeddings table is empty (prints a notification).
    - search_semantic raises an unexpected exception.

    Args:
        natural_language: When True, uses keyword AND-search for BM25 instead
            of full-phrase matching. Pass True for Ask Brain / free-form questions.
    """
    bm25 = search_notes(conn, query, limit=limit * 2, natural_language=natural_language)

    try:
        vec_results = search_semantic(conn, query, limit=limit * 2)
    except Exception:
        return bm25[:limit]

    if not vec_results:
        # search_semantic already printed a notification if relevant
        return bm25[:limit]

    merged = _rrf_merge(bm25, vec_results, k=60, limit=limit)
    return _enrich_with_excerpts(conn, merged, query)


def _apply_filters(
    results: list[dict],
    conn: sqlite3.Connection,
    person: str | None = None,
    tag: str | None = None,
    note_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    importance: str | None = None,
) -> list[dict]:
    """Post-filter search results by entity dimensions. AND logic.

    All params are optional (None = skip that filter). Multiple filters applied
    in combination require a result to satisfy ALL provided conditions.

    Args:
        results: List of result dicts (from search_hybrid / search_notes).
        conn: SQLite connection (needed for tag/person lookups).
        person: Filter to notes where this name appears in the people column.
        tag: Filter to notes that have this tag in the note_tags junction table.
        note_type: Filter to notes where type equals this value.
        from_date: ISO date string (YYYY-MM-DD). Exclude notes created before this date.
        to_date: ISO date string (YYYY-MM-DD). Exclude notes created after this date.

    Returns:
        Filtered list of result dicts.
    """
    if not any([person, tag, note_type, from_date, to_date, importance]):
        return results

    filtered = []
    for r in results:
        if note_type and r.get("type") != note_type:
            continue
        if from_date and r.get("created_at", "") < from_date:
            continue
        if to_date and r.get("created_at", "") > to_date + "T23:59:59":
            continue
        if tag:
            tag_rows = conn.execute(
                "SELECT tag FROM note_tags WHERE note_path=?", (r["path"],)
            ).fetchall()
            tag_set = {row[0] for row in tag_rows}
            if tag not in tag_set:
                continue
        if person:
            people_row = conn.execute(
                "SELECT people FROM notes WHERE path=?", (r["path"],)
            ).fetchone()
            plist = _json.loads(people_row[0] or "[]") if people_row else []
            if not any(person in p or p == person for p in plist):
                continue
        if importance:
            imp_row = conn.execute(
                "SELECT importance FROM notes WHERE path=?", (r["path"],)
            ).fetchone()
            if not imp_row or imp_row[0] != importance:
                continue
        filtered.append(r)
    return filtered


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
