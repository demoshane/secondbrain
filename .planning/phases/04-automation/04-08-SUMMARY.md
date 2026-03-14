---
phase: 04-automation
plan: "08"
subsystem: init
tags: [templates, init, paths, shutil]

requires:
  - phase: 04-automation/04-03
    provides: init_brain.py create_brain_structure pattern (config.toml seeding model)

provides:
  - .meta/templates added to BRAIN_SUBDIRS in engine/paths.py
  - seed_templates() in engine/init_brain.py — idempotent copy from repo to brain root
  - 5 skeleton template files in brain/.meta/templates/ (people, meeting, projects, coding, strategy)

affects: [init, templates, capture, reindex]

tech-stack:
  added: [shutil]
  patterns:
    - "seed_templates() mirrors config.toml seeding pattern — idempotent, no overwrite"
    - "BRAIN_SUBDIRS drives mkdir loop; .meta/templates added so init creates the dir automatically"

key-files:
  created:
    - brain/.meta/templates/people.md
    - brain/.meta/templates/meeting.md
    - brain/.meta/templates/projects.md
    - brain/.meta/templates/coding.md
    - brain/.meta/templates/strategy.md
  modified:
    - engine/paths.py
    - engine/init_brain.py
    - tests/test_paths.py

key-decisions:
  - "seed_templates() source path is Path(__file__).parent.parent / 'brain' / '.meta' / 'templates' — relative to engine/, not to brain_root, so repo templates are always found regardless of brain_root location"
  - "Existing files are never overwritten — idempotent copy matches config.toml seeding contract"
  - "BRAIN_SUBDIRS count updated from 9 to 10 in test_paths.py — count assertion must track intentional additions"

patterns-established:
  - "Template seeding: copy repo/.meta/templates → brain_root/.meta/templates on init, skip if exists"

requirements-completed: [PEOPLE-01, PEOPLE-02, WORK-01, WORK-02, WORK-03, WORK-04]

duration: 12min
completed: 2026-03-14
---

# Phase 4 Plan 08: Templates Init Summary

**`.meta/templates` directory and 5 skeleton template files (people, meeting, projects, coding, strategy) seeded during sb-init via idempotent seed_templates() modelled on config.toml seeding pattern**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-14T18:30:00Z
- **Completed:** 2026-03-14T18:42:00Z
- **Tasks:** 2
- **Files modified:** 5 template files + engine/paths.py + engine/init_brain.py + tests/test_paths.py

## Accomplishments

- Added `.meta/templates` to BRAIN_SUBDIRS so init automatically creates the directory
- Added `seed_templates()` to `engine/init_brain.py` — copies repo skeletons to brain root on first init, never overwrites
- Called `seed_templates()` from `create_brain_structure()` after subdirs loop (mirrors config.toml seeding at lines 92-109)
- Wrote 5 meaningful skeleton template files with `{{placeholder}}` variables and `## Backlinks` sections
- Full test suite green: 89 passed, 4 skipped, 1 xfailed

## Task Commits

Each task was committed atomically:

1. **Task 1: Add .meta/templates to BRAIN_SUBDIRS and create seed_templates()** - `78a75c1` (feat)
2. **Task 2: Create 5 skeleton template files in brain/.meta/templates/** - `4354faa` (feat)

## Files Created/Modified

- `engine/paths.py` - Added `.meta/templates` to BRAIN_SUBDIRS list (now 10 entries)
- `engine/init_brain.py` - Added `import shutil`, `seed_templates()` function, called from `create_brain_structure()`
- `brain/.meta/templates/people.md` - name/role/company/contact/notes/backlinks skeleton
- `brain/.meta/templates/meeting.md` - title/date/attendees/project/agenda/notes/action-items/backlinks
- `brain/.meta/templates/projects.md` - title/status/started/goal/context/progress/next-steps/backlinks
- `brain/.meta/templates/coding.md` - title/date/language-stack/tags/problem/solution/code/references/backlinks
- `brain/.meta/templates/strategy.md` - title/date/horizon/situation/options/decision/rationale/backlinks
- `tests/test_paths.py` - Updated BRAIN_SUBDIRS count assertion from 9 to 10

## Decisions Made

- `seed_templates()` source path computed relative to `__file__` (engine/) not brain_root — ensures repo templates always found
- Existing files never overwritten — matches config.toml seeding contract, safe to re-run init
- BRAIN_SUBDIRS count assertion updated: test must track intentional list additions or it becomes a false gate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale BRAIN_SUBDIRS count assertion in tests/test_paths.py**
- **Found during:** Task 2 (full test suite run after creating template files)
- **Issue:** `test_paths_module_exports_expected_symbols` asserted `len(BRAIN_SUBDIRS) == 9`; adding `.meta/templates` made it 10 causing test failure
- **Fix:** Updated assertion to `== 10`
- **Files modified:** tests/test_paths.py
- **Verification:** Full suite passes — 89 passed, 4 skipped, 1 xfailed
- **Committed in:** `4354faa` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (stale test count assertion)
**Impact on plan:** Necessary correctness fix — test was asserting a count that became wrong after the planned change.

## Issues Encountered

- Pre-commit hook stash/restore cycle unstages files between `git add` and `git commit` — required re-staging before each commit attempt. Pre-existing behaviour; worked around by re-adding after the hook ran.

## Next Phase Readiness

- Templates seeded on init; `engine/templates.py` `load_template()` can now find real files instead of falling back to inline defaults
- Test 5 (templates init gap) should now pass
- Ready for plan 09 (further automation gap closures)

---
*Phase: 04-automation*
*Completed: 2026-03-14*
