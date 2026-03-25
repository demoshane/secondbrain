---
phase: 37-housekeeping
plan: 07
status: complete
---

# 37-07 Summary — Embedding reindex test race condition fix

## What was done
Fixed 4 long-failing `TestReindexGeneratesEmbeddings` tests by adding a `synchronous=True` parameter to `reindex_brain()`. The root cause was a race condition: `embed_pass_async()` opens a new DB connection in a background thread, which sees an empty database when tests use in-memory/tmp SQLite. With `synchronous=True`, `embed_pass()` runs on the caller's existing connection instead.

## Changes
- `engine/reindex.py`: Added `synchronous: bool = False` param to `reindex_brain`; added conditional to call `embed_pass(conn, ...)` directly when `synchronous=True`, falling back to `embed_pass_async` for production.
- `tests/test_embeddings.py`: Updated all 7 `reindex_brain()` calls inside `TestReindexGeneratesEmbeddings` to pass `synchronous=True`.

## Verification
- `uv run pytest tests/test_embeddings.py::TestReindexGeneratesEmbeddings -v` — 4 passed (previously all failing)
- `uv run pytest tests/test_embeddings.py` — 22 passed, 0 failed

## Decisions
- `synchronous=False` default preserves all production behaviour — no callers outside tests need updating.
- Condition is `synchronous and conn is not None` — safe guard against passing `synchronous=True` without a connection.
