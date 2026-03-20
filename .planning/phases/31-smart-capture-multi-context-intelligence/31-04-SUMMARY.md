# Plan 31-04 Summary: Bidirectional Links + Batch Dedup + Sensitivity

## Status: Complete

## What was built
- `sb_link` accepts `bidirectional=True` — inserts both A->B and B->A rows
- `sb_capture_batch` enhanced: links field processing with slug resolution, per-note sensitivity auto-classify via `classify_smart`, per-note dedup warnings, intra-batch title dedup via fuzzy match (cutoff 0.85)
- `sb_capture` auto-classifies sensitivity (never downgrade)
- Return includes `dedup_warnings` array

## Key decisions
- Dedup warnings are informational, not blocking — notes still save
- Short body (<50 chars) skips dedup check to avoid false positives
- Links resolved by title match first, then path LIKE fallback
- Bidirectional links create two rows (not one with OR query) for simplicity

## Commits
- `8be8edd` feat(31-04): bidirectional links, batch dedup warnings, sensitivity auto-classify
