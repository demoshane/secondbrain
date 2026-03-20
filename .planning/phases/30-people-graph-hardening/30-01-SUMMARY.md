---
phase: 30-people-graph-hardening
plan: "01"
subsystem: entity-extraction
tags: [entities, people, unicode, capture, db]
dependency_graph:
  requires: []
  provides: [unicode-entity-extraction, people-write-back, org-extraction, people-db-index]
  affects: [engine/entities.py, engine/capture.py, engine/db.py, engine/links.py]
tech_stack:
  added: []
  patterns:
    - Unicode Extended Latin character class ranges in stdlib re
    - Retry-on-stop-word extraction for greedy regex
    - Entity extraction before build_post() for people write-back
key_files:
  created: [tests/test_entities.py (rewritten)]
  modified:
    - engine/entities.py
    - engine/capture.py
    - engine/db.py
    - engine/links.py
    - tests/test_capture.py
decisions:
  - "[30-01] _extract_people uses re.finditer with pos-retry so stop-word first tokens allow re-match from second token — avoids consuming 'Anna' in 'Met Anna Korhonen'"
  - "[30-01] _WORD and _NAME_SEG kept separate — apostrophe names (O'Brien) modelled as _APOSTROPHE_NAME alternative, not via _LC inclusion, to avoid trailing-char greediness"
  - "[30-01] Org extraction suffix-based only — no pure acronym matching per research recommendation"
  - "[30-01] Expanded stop words include verbs (Met, Had), common nouns (Team, Sprint, Planning), day/month names to reduce false positives"
  - "[30-01] ensure_person_profile() gets mkdir(parents=True) — pre-existing missing-dir bug caught by new tests (Rule 1 auto-fix)"
  - "[30-01] idx_notes_people is a plain index, not a generated column — generated column adds no benefit for JSON LIKE queries per research"
  - "[30-01] entity extraction order changed: extract → merge → build_post(merged) → write, was: build_post → extract → write (Pitfall 3 from research)"
metrics:
  duration: "25 min"
  completed: "2026-03-20"
  tasks_completed: 2
  files_modified: 5
---

# Phase 30 Plan 01: Unicode Entity Extraction + People Write-Back Summary

Unicode-aware Extended Latin name extraction with Finnish stop words, org extraction, and people column write-back at capture time via restructured entity extraction order.

## What Was Built

### Task 1: Unicode Entity Extraction + Org Extraction

**engine/entities.py** rewritten with:

- `_UC` / `_LC` character classes covering Basic Latin + Latin-1 Supplement + Latin Extended-A/B (Finnish ä/ö, Nordic å/ø/æ, French é/è/ê, German ü, etc.)
- `_APOSTROPHE_NAME` pattern for O'Brien-style names (U+0027 and U+2019)
- `_NAME_SEG` for hyphenated last names (Mäki-Petäjä)
- `_PREFIX` regex for compound prefixes: van/von/de/di/la/el plus two-word variants (van der, van den)
- `_FINNISH_STOPS` frozenset: Mutta, Koska, Että, Jos, Vaikka, etc.
- Expanded `_STOP_WORDS`: added verbs (Met, Had, Was), common nouns (Team, Sprint, Planning, Project, Summary), day/month names
- `_extract_people()` uses `re.finditer` with pos-retry on stop-word first tokens so "Met Anna Korhonen" → "Anna Korhonen" not nothing
- `_extract_organizations()` suffix-based: Ltd, Oy, GmbH, Inc, Corp, AB, AS, SA, LLC, plc, Group, Agency, Studio, etc. No pure acronyms
- `extract_entities()` returns `{"people", "places", "topics", "orgs"}` — added `orgs` key

### Task 2: People Write-Back + DB Index

**engine/capture.py** restructured:
- Entity extraction moved BEFORE `build_post()` (critical order fix — Pitfall 3)
- `merged_people = list(dict.fromkeys(people + extracted_people))` — caller first, dedup preserve order
- `merged_people` passed to both `build_post()` and `add_backlinks()`

**engine/db.py**:
- Added `CREATE INDEX IF NOT EXISTS idx_notes_people ON notes(people)` to `init_schema()`

**engine/links.py** (Rule 1 auto-fix):
- `ensure_person_profile()` now calls `person_file.parent.mkdir(parents=True, exist_ok=True)` before `write_text` — was silently failing when brain_root/person/ didn't exist

## Tests Written

### test_entities.py (21 tests)
- `test_existing_ascii_names_still_work` — regression guard
- `test_extract_finnish_names` — Leppanen extracts
- `test_extract_nordic_names` — Lindqvist, Ostergren
- `test_extract_name_with_a_umlaut / o_umlaut` — Unicode diacritics
- `test_extract_compound_hyphenated_names` — Maki-Petaja
- `test_extract_van_prefix_names` — van der Berg
- `test_extract_obrien_style_names` — O'Brien
- `test_finnish_stopwords_not_extracted` — Mutta Koska
- `test_english_stopwords_still_filtered` — The This
- `test_extract_orgs_oy / inc / gmbh` — suffix-based org extraction
- `test_org_no_acronym_false_positives` — API, MCP not in orgs
- `test_title_body_processed_separately` — Phase 27.1 regression guard

### test_capture.py (3 new tests)
- `test_capture_people_writeback` — body-extracted people in DB people column
- `test_capture_people_merge` — explicit + extracted people both present
- `test_capture_people_dedup` — no duplicate when same person in both sources

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ensure_person_profile() missing mkdir**
- **Found during:** Task 2 — test_capture_people_writeback failed with FileNotFoundError
- **Issue:** `brain_root/person/` directory not created before `write_text()`; fails on first capture to a brain_root without the person subdir
- **Fix:** Added `person_file.parent.mkdir(parents=True, exist_ok=True)` in `ensure_person_profile()`
- **Files modified:** engine/links.py
- **Commit:** 3dcd2d8

**2. [Rule 1 - Bug] Greedy regex consuming stop-word first tokens**
- **Found during:** Task 2 implementation — "Met Anna Korhonen" yielded nothing after "Met" was added to stops, because regex consumed "Anna" in the stopped match
- **Issue:** `re.findall` with stop-word filter leaves the second word unconsumed; "Anna Korhonen" never matched
- **Fix:** Rewrote `_extract_people()` to use `re.finditer` with manual position tracking; when first word is a stop word, retry from `m.start(2)` (position of the second group)
- **Files modified:** engine/entities.py
- **Commit:** f38dd49

**3. [Rule 1 - Bug] "Team Update", "Sprint Planning" extracted as false positive names**
- **Found during:** Task 2 — title "Team Update" produced people: ["Team Update"]
- **Issue:** Common noun phrases in Title Case are false positives
- **Fix:** Expanded _STOP_WORDS with common nouns (Team, Sprint, Planning, Project, Summary, etc.), day/month names
- **Files modified:** engine/entities.py
- **Commit:** f38dd49 (expanded in same commit)

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| engine/entities.py exists | FOUND |
| engine/capture.py exists | FOUND |
| engine/db.py exists | FOUND |
| engine/links.py exists | FOUND |
| tests/test_entities.py exists | FOUND |
| tests/test_capture.py exists | FOUND |
| commit f38dd49 exists | FOUND |
| commit 3dcd2d8 exists | FOUND |
| idx_notes_people in db.py | FOUND |
| merged_people in capture.py | FOUND |
| 35 passed, 2 xpassed (test_entities + test_capture) | PASSED |
