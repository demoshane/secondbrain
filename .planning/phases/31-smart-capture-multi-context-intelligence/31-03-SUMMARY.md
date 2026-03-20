# Plan 31-03 Summary: Dormant Resurfacing + Async Intelligence Hooks

## Status: Complete

## What was built
- `find_dormant_related()` in `engine/intelligence.py` — finds semantically similar notes not updated in 30+ days
- Dormant notes in `sb_capture` response (`dormant_notes` key)
- Dormant notes in `sb_capture_smart` response
- Similar auto-link: `sb_capture` with confirm_token creates `similar` relationship rows
- Async intelligence hooks in `sb_capture_batch` — background daemon thread runs `check_connections` + `extract_action_items` per note
- Error isolation: hook failures logged to `audit_log` with `event_type='intelligence_error'`

## Key decisions
- Dormant threshold: `find_similar(threshold=0.5)` with 30-day age filter
- Async hooks use per-note `get_connection()` (own transaction per hook call)
- Implementation was pre-built by 31-01 executor; this plan focused on test promotion and bug fixes

## Bug fixed
- `audit_log` column name: test used `action` but schema defines `event_type`

## Tests promoted from xfail
- `test_dormant_resurfacing` (CAP-04)
- `test_async_hooks_nonblocking` (CAP-06)
- `test_sensitivity_classify_smart` (CAP-10)
- `test_batch_dedup_warnings` (CAP-11)
- `test_smart_capture_performance` (CAP-PERF)
- `test_similar_relationship_inserted_on_confirm` (CAP-05)

## Commits
- `ab5eba5` feat(31-02,31-03): promote xfail stubs, fix audit_log column, test fixes
