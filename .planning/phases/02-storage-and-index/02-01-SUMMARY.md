---
phase: 02-storage-and-index
plan: "01"
subsystem: database
tags: [sqlite, python-frontmatter, capture, templates, atomic-write, gdpr]

requires:
  - phase: 02-00
    provides: "Test stubs (test_capture.py, test_audit.py) and conftest fixtures (initialized_db, seeded_db)"
  - phase: 01-foundation
    provides: "engine/db.py schema, engine/paths.py TEMPLATES_DIR, pyproject.toml with python-frontmatter dep"

provides:
  - "engine/capture.py: build_post, write_note_atomic, log_audit, capture_note"
  - "engine/templates.py: load_template, render_template"
  - "engine/db.py: migrate_add_people_column (idempotent, auto-called from init_schema)"
  - "6 per-type markdown body templates in brain/.meta/templates/"

affects:
  - 02-02-search
  - 03-cli
  - 04-ai-integration

tech-stack:
  added: []
  patterns:
    - "Two-phase atomic write: mkstemp(dir=target.parent) → DB commit → os.replace"
    - "GDPR-safe errors: type(e).__name__ only, never body/metadata in error messages"
    - "safe_substitute for templates: missing placeholders left as-is, never raises"
    - "Idempotent migration pattern: PRAGMA table_info check before ALTER TABLE"

key-files:
  created:
    - engine/capture.py
    - engine/templates.py
    - brain/.meta/templates/note.md
    - brain/.meta/templates/meeting.md
    - brain/.meta/templates/people.md
    - brain/.meta/templates/coding.md
    - brain/.meta/templates/strategy.md
    - brain/.meta/templates/idea.md
  modified:
    - engine/db.py
    - tests/test_capture.py

key-decisions:
  - "Temp file always in target.parent via mkstemp(dir=target.parent) — never /tmp — guarantees atomic os.replace on same filesystem"
  - "conn.commit() happens before os.replace() — DB is source of truth; partial file never exists without a DB record"
  - "Error messages use f'Failed to write {target}: {type(e).__name__}' — path is safe to expose, body/metadata are not"
  - "load_template accepts optional templates_dir override for testability without touching TEMPLATES_DIR global"
  - "migrate_add_people_column called at end of init_schema so any existing Phase 1 DB is automatically upgraded"

patterns-established:
  - "Atomic write pattern: temp-in-same-dir + DB commit + rename — use for all future note mutations"
  - "GDPR error pattern: never interpolate post content/metadata into exception messages"
  - "Template override pattern: engine functions accept optional path overrides for hermetic testing"

requirements-completed: [CAP-01, CAP-02, CAP-03, CAP-07, GDPR-05]

duration: 3min
completed: 2026-03-14
---

# Phase 2 Plan 01: Capture Pipeline Summary

**Atomic two-phase write with GDPR-safe errors, 8-field YAML frontmatter via python-frontmatter, per-type body templates, and idempotent people-column DB migration**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T15:30:28Z
- **Completed:** 2026-03-14T15:33:28Z
- **Tasks:** 2
- **Files modified:** 10 (3 engine modules, 6 templates, 1 test file)

## Accomplishments

- Implemented `write_note_atomic`: temp file in same dir as target, DB INSERT + audit log committed before `os.replace`, temp cleanup on any failure
- `build_post` generates all 8 required frontmatter fields (type, title, date, tags, people, created_at, updated_at, content_sensitivity)
- `migrate_add_people_column` auto-runs from `init_schema` — idempotent PRAGMA check ensures safe upgrade of Phase 1 databases
- 6 per-type body templates created with `${variable}` placeholders loaded by `engine/templates.py`
- All 5 `test_capture.py` tests pass; 34 tests pass, 3 skipped in full suite (no regressions)

## Task Commits

1. **RED: Failing capture tests** - `63b722a` (test)
2. **GREEN: DB migration + capture + templates** - `3bbc8ef` (feat)
3. **Task 2: Per-type template files** - `8522aaa` (feat)

## Files Created/Modified

- `engine/capture.py` - build_post, write_note_atomic, log_audit, capture_note
- `engine/templates.py` - load_template (pathlib-only), render_template (safe_substitute)
- `engine/db.py` - Added migrate_add_people_column, called from init_schema
- `tests/test_capture.py` - Real test implementations (replaced stubs)
- `brain/.meta/templates/note.md` - Generic note body template
- `brain/.meta/templates/meeting.md` - Meeting with attendees, agenda, action items sections
- `brain/.meta/templates/people.md` - People with profile, notes, growth discussion sections
- `brain/.meta/templates/coding.md` - ADR-style with context, decision, consequences sections
- `brain/.meta/templates/strategy.md` - Strategy with objective, key results, status sections
- `brain/.meta/templates/idea.md` - Idea with elaboration and next steps sections

## Decisions Made

- Temp file always uses `mkstemp(dir=target.parent)` — same filesystem guarantees `os.replace` is atomic
- `conn.commit()` before `os.replace()` — if the process dies between commit and rename, DB has a record but file is missing; reindex handles this; the reverse (file exists, no DB record) is the worse failure mode
- Error format is `f"Failed to write {target}: {type(e).__name__}"` — target path is safe to log; body/metadata are never included (GDPR-05)
- `load_template` accepts `templates_dir` keyword override so tests don't touch the container-only `/workspace/brain` path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added `# pragma: allowlist secret` to test fixture string**
- **Found during:** Task 1 RED commit
- **Issue:** `detect-secrets` hook flagged the string `"SUPER SECRET BODY CONTENT XYZ"` in the test as a potential secret, blocking the commit
- **Fix:** Added `# pragma: allowlist secret` inline comment — standard pattern already established in Phase 1 (test_blocks_api_key)
- **Files modified:** tests/test_capture.py
- **Verification:** Pre-commit hook passed on retry
- **Committed in:** 63b722a (RED test commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — pre-commit false positive)
**Impact on plan:** No scope change. Fix is a single inline comment consistent with Phase 1 convention.

## Issues Encountered

- Pre-existing stubs in `test_audit.py` and `test_search.py` fail (they are Plan 02/03 placeholders with `# fails until Plan 02` comments). Excluded from regression check — these are expected failures, not regressions.

## Next Phase Readiness

- Capture pipeline complete — Plan 02 (search) can now run in parallel as planned
- `engine/capture.py` exports (`write_note_atomic`, `build_post`, `log_audit`, `capture_note`) ready for CLI wiring in Phase 3
- `initialized_db` fixture already applies people-column migration, so Plan 02 search tests will work against correct schema

---
*Phase: 02-storage-and-index*
*Completed: 2026-03-14*
