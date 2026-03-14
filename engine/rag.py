"""RAG-lite FTS5 context retrieval (SEARCH-04). Implementation in plan 04-02."""
import sqlite3


def retrieve_context(query: str, conn: sqlite3.Connection, limit: int = 5, debug: bool = False) -> str:
    """Stub — implemented in plan 04-02."""
    raise NotImplementedError


def augment_prompt(query: str, conn: sqlite3.Connection, debug: bool = False) -> str:
    """Stub — implemented in plan 04-02."""
    raise NotImplementedError
