"""RAG-lite FTS5 context retrieval (SEARCH-04).

AI-10 compliance: context is injected into user_content only, never system_prompt.
"""
from pathlib import Path
import sqlite3
from engine.search import search_notes

CONTEXT_HEADER = "=== RETRIEVED CONTEXT (from second brain FTS5 search) ==="
CONTEXT_FOOTER = "=== END RETRIEVED CONTEXT ==="
_BODY_TRUNCATE = 500  # chars per note


def retrieve_context(
    query: str,
    conn: sqlite3.Connection,
    limit: int = 5,
    debug: bool = False,
) -> str:
    """Return formatted context block of top-N FTS5 results for injection into user_content.

    Returns empty string if no results found.
    """
    results = search_notes(conn, query, limit=limit)
    if not results:
        return ""

    blocks = [CONTEXT_HEADER]
    for r in results:
        note_path = Path(r["path"])
        try:
            body = note_path.read_text(encoding="utf-8")[:_BODY_TRUNCATE]
        except OSError:
            body = "[note file not readable]"
        blocks.append(f"\n[{r['title']}] ({r['path']})\n{body}")
        if debug:
            print(f"[RAG] Retrieved: {r['title']} (score={r.get('score', '?')})")
    blocks.append(CONTEXT_FOOTER)
    return "\n".join(blocks)


def augment_prompt(query: str, conn: sqlite3.Connection, debug: bool = False) -> str:
    """Return user_content with RAG context prepended.

    If no context found, returns query unchanged.
    Context is in user_content — never pass this to system_prompt (AI-10).
    """
    context = retrieve_context(query, conn, debug=debug)
    if context:
        return f"{context}\n\n---\n\n{query}"
    return query
