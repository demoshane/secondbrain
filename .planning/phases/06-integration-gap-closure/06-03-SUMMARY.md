---
phase: 06-integration-gap-closure
plan: "03"
subsystem: documentation
tags: [subagent, claude-code, capture, gdpr, proactive-capture]

requires:
  - phase: 06-02
    provides: CAP-06 memory update call site — subagent now has full capture→memory pipeline to document
  - phase: 03-ai-layer
    provides: second-brain subagent file (.claude/agents/second-brain.md) and install_subagent.py

provides:
  - ".claude/agents/second-brain.md fully documents all 5 sb-* commands with args and examples"
  - "~/.claude/CLAUDE.md has proactive capture instructions (Second Brain section)"
  - "Claude Cowork equivalence section in subagent spec"

affects:
  - future-sessions
  - claude-code-interface
  - second-brain-subagent

tech-stack:
  added: []
  patterns:
    - "Idempotency guard: check for section header before appending to config files"
    - "Subagent spec as single source of truth for command documentation"

key-files:
  created: []
  modified:
    - ".claude/agents/second-brain.md — expanded with all 5 sb-* command docs and Cowork equivalence section"
    - "~/.claude/CLAUDE.md — appended Second Brain proactive capture section (outside repo)"

key-decisions:
  - "CAP-09 target (~/.claude/CLAUDE.md) lives outside repo — no repo commit for that file; checkpoint used for manual verification"
  - "Idempotency guard added to CLAUDE.md append: skip if ## Second Brain already present"

patterns-established:
  - "Out-of-repo config files use checkpoint:human-verify for confirmation rather than automated test"

requirements-completed:
  - CAP-08
  - CAP-09

duration: 15min
completed: 2026-03-15
---

# Phase 6 Plan 03: Documentation — Subagent Spec and Proactive Capture Summary

**All 5 sb-* commands documented in .claude/agents/second-brain.md with args and examples; ~/.claude/CLAUDE.md gains proactive capture instructions with re-offer policy**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-15
- **Completed:** 2026-03-15
- **Tasks:** 2
- **Files modified:** 2 (.claude/agents/second-brain.md in repo; ~/.claude/CLAUDE.md outside repo)

## Accomplishments

- Expanded second-brain subagent spec to document all 5 commands (sb-capture, sb-search, sb-forget, sb-read, sb-check-links) with full argument tables and usage examples
- Added Claude Cowork equivalence section so the spec applies to both Claude Code and Cowork sessions
- Appended `## Second Brain` proactive capture block to ~/.claude/CLAUDE.md with offer phrasing, sb-capture usage, content type guidance, and re-offer policy (idempotent — skips if section already present)

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand second-brain subagent spec (CAP-08)** - `017faac` (feat)
2. **Task 2: Append Second Brain section to ~/.claude/CLAUDE.md (CAP-09)** - verified via checkpoint; no in-repo file to commit

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `.claude/agents/second-brain.md` — expanded body with all 5 sb-* command sections and Claude Cowork Equivalence section
- `/Users/tuomasleppanen/.claude/CLAUDE.md` — appended `## Second Brain` proactive capture block (outside repo, confirmed via checkpoint)

## Decisions Made

- CAP-09 target lives outside the repo — used checkpoint:human-verify instead of an automated test; user confirmed section present and correct
- Idempotency guard specified in plan: if `## Second Brain` already present, skip append (no duplicate section created)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 06 is the final integration gap closure phase; all 4 plans (06-00 through 06-03) are now complete
- CAP-08 and CAP-09 are satisfied: Claude Code can invoke second-brain subagent and will proactively offer capture
- Project is ready for v1.0 audit / final verification pass

---
*Phase: 06-integration-gap-closure*
*Completed: 2026-03-15*
