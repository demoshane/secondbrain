---
phase: 04-automation
plan: "03"
subsystem: templates
tags: [templates, capture, ai, type-routing]

requires:
  - phase: 04-00
    provides: phase 4 foundation plan with capture pipeline and type system

provides:
  - projects.md template with Client/Account, Key Contacts, Status, Meeting History
  - strategy.md updated with frontmatter and Linked Initiatives section
  - coding.md updated with frontmatter, Alternatives Considered, GitHub Repo sections
  - people.md updated with Growth Discussion History and Meetings & References sections
  - TYPE_TO_DIR mapping fixing idea -> ideas/ subdir in capture.py
  - projects and personal added to --type choices and ai.py prompts

affects: [capture, ai-layer, templates, test-links]

tech-stack:
  added: []
  patterns:
    - "TYPE_TO_DIR dict pattern for CLI type -> subdir name translation (extensible)"
    - "People notes use name-only slug (no date prefix) for stable addressability"

key-files:
  created:
    - brain/.meta/templates/projects.md
  modified:
    - brain/.meta/templates/strategy.md
    - brain/.meta/templates/coding.md
    - brain/.meta/templates/people.md
    - engine/capture.py
    - engine/ai.py

key-decisions:
  - "TYPE_TO_DIR dict used for type->subdir mapping — allows future additions without touching path construction logic"
  - "People notes slug omits date prefix — person profiles addressed by name, not creation date"
  - "projects and personal types added symmetrically to both QUESTION_SYSTEM_PROMPTS and FALLBACK_QUESTIONS in ai.py"

patterns-established:
  - "Template files include YAML frontmatter with all 8 standard fields for consistency with captured notes"
  - "TYPE_TO_DIR.get(note_type, note_type) as default passthrough — new types work without explicit registration"

requirements-completed: [PEOPLE-01, PEOPLE-02, WORK-01, WORK-02, WORK-03, WORK-04]

duration: 12min
completed: 2026-03-14
---

# Phase 4 Plan 03: Templates and Type Extension Summary

**New projects.md template plus TYPE_TO_DIR fix routing idea notes to ideas/ subdir, people slug without date prefix, and projects/personal types wired into capture CLI and AI prompts**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-14T17:35:00Z
- **Completed:** 2026-03-14T17:47:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Created `brain/.meta/templates/projects.md` with Client/Account, Key Contacts, Status, Meeting History sections (WORK-02)
- Updated `strategy.md`, `coding.md`, `people.md` with missing sections and YAML frontmatter
- Fixed `idea` type routing to `ideas/` subdir via `TYPE_TO_DIR` dict in `capture.py`
- Added `projects` and `personal` to `--type` argparse choices and `ai.py` system prompts/fallback questions
- People notes now use name-only slug for stable cross-note linking

## Task Commits

Each task was committed atomically:

1. **Task 1: Create projects.md template and update existing templates** - `509b4cb` (feat)
2. **Task 2: Fix idea/ideas subdir mismatch and add projects + personal types** - `78f6fd3` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `brain/.meta/templates/projects.md` - New template for client/project notes with Key Contacts and Meeting History
- `brain/.meta/templates/strategy.md` - Added YAML frontmatter and Linked Initiatives section
- `brain/.meta/templates/coding.md` - Added YAML frontmatter, Alternatives Considered, GitHub Repo sections
- `brain/.meta/templates/people.md` - Renamed Growth Discussions to Growth Discussion History; added Meetings & References section
- `engine/capture.py` - Added TYPE_TO_DIR, subdir routing fix, people slug override, projects/personal choices
- `engine/ai.py` - Added projects and personal entries to QUESTION_SYSTEM_PROMPTS and FALLBACK_QUESTIONS

## Decisions Made

- `TYPE_TO_DIR` as a top-level module dict rather than inline — makes it easy to add future remappings (e.g. `note -> notes`) without touching path logic
- People slug without date prefix chosen so `[[people/alice-smith]]` links remain stable regardless of when the profile was created
- `projects` and `personal` prompts added symmetrically to both `QUESTION_SYSTEM_PROMPTS` and `FALLBACK_QUESTIONS` to ensure graceful degradation when AI is unavailable

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

Pre-existing failures in `tests/test_links.py::test_cli_no_orphans` (tries to set readonly `__globals__` attribute) and `tests/test_rag.py` (stubs raising `NotImplementedError`) were observed but are out of scope for this plan. These exist from earlier phase stubs. Target tests `test_capture.py` and `test_ai.py` all pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All WORK-01 through WORK-04 and PEOPLE-01/PEOPLE-02 template requirements fulfilled
- `test_links.py::test_work_templates_exist` should now pass (was blocked on missing projects.md)
- Ready for phase 4 remaining plans (04-04 onwards)

---
*Phase: 04-automation*
*Completed: 2026-03-14*
