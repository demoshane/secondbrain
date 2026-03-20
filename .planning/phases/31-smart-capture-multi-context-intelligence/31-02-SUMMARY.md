# Plan 31-02 Summary: Entity Resolution + Dedup Heuristics

## Status: Complete

## What was built
- `resolve_entities()` in `engine/segmenter.py` — FTS5 + fuzzy match for existing person/project notes, stub creation for new entities
- `dedup_segment()` in `engine/segmenter.py` — three-path dedup heuristic (save_new/update_existing/save_complementary/ambiguous)
- Wired into `sb_capture_smart`: entity stubs created before main segments, dedup per segment, co-captured relationships

## Key decisions
- Entity resolution uses FTS5 first, falls back to `difflib.get_close_matches(cutoff=0.75)`
- Superset check: body >1.2x longer AND 2+ key phrases overlap → update existing with changelog
- Implementation was pre-built by 31-01 executor; this plan focused on test promotion and validation

## Tests promoted from xfail
- `test_entity_resolution_links_existing` (CAP-08)
- `test_multi_context_atomic_save` (CAP-02)
- `test_dedup_three_path` (CAP-03)
- `test_similar_relationship_created` (CAP-05)
- `test_bidirectional_relationships` (CAP-07)
- `test_batch_links_field` (CAP-09)

## Commits
- `ab5eba5` feat(31-02,31-03): promote xfail stubs, fix audit_log column, test fixes
