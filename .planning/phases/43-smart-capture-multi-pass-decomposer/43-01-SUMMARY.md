---
plan: 43-01
status: complete
date: 2026-03-29
---

# 43-01 Summary — Pass Architecture + Types + TypeClassifier Fix

## What was built

### engine/passes/ package (4 files)
- `__init__.py` — `DecomposedResult`, `LinkNote`, `ActionItem` dataclasses + `decompose()` orchestrator + `CONFIDENCE_THRESHOLD` re-export
- `p1_entities.py` — `extract_all_entities(content)` wrapping `engine.entities.extract_entities`
- `p2_urls.py` — `extract_urls(content) -> (stripped_body, list[LinkNote])` strips URLs, produces LinkNote per unique URL
- `p3_classify.py` — `classify_content(title, body)` with `_CONVO_TURN_PAT` + `_conversation_boost()` implementing D-11 conversation signal

### engine/typeclassifier.py
- Removed URL hard-override (`if _URL_PAT.search(combined): return ("link", 1.0)`)
- Added competitive link scoring: 0.85 when URL dominates content (stripped < 50 chars), 0.70 when URL present with substantive content
- Meeting note with Zoom URL now classifies as "meeting" correctly

### engine/db.py (pre-existing bug fix)
- `_migrate_fk_cascade` forgot `description` column when recreating `action_items` with FK CASCADE
- Added `if "description" in ai_cols: extra_defs.append("description TEXT NULL")` — unblocked all tests

### tests/test_decomposer.py (26 tests)
- `TestDecomposeShape`, `TestPass1Entities`, `TestPass2Urls`, `TestPass3Classify`, `TestConversationSignal`, `TestDecomposeIntegration`

### tests/test_typeclassifier.py (updated)
- `test_url_gives_link` — updated assertion to `>= CONFIDENCE_THRESHOLD` (no longer asserts `1.0`)
- Added `test_meeting_with_url_classifies_as_meeting`
- Added `test_url_only_body_classifies_as_link`

## Verification

```
44 passed in 0.94s
from engine.passes import decompose, DecomposedResult, LinkNote, ActionItem, CONFIDENCE_THRESHOLD  # OK
```

## Notes

- Circular import pattern (`__init__.py` defines `LinkNote` before importing `p2_urls`) works correctly — `LinkNote` is in the module namespace when `p2_urls` does `from engine.passes import LinkNote`
- `decompose()` reuses segmenter.py private functions (`_mask_protected_regions`, `_split_at_safe_positions`, etc.) — these will be consolidated in Plan 43-03 when `segment_blob()` is deleted
- DB bug was blocking ALL tests (via `gui_brain` session fixture + `init_schema()`) — fixed as prerequisite
