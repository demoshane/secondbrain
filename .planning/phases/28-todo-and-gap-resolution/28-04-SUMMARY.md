---
phase: 28-todo-and-gap-resolution
plan: "04"
subsystem: mcp
tags: [mcp, relationships, links, tdd]
dependency_graph:
  requires: []
  provides: [sb_link-mcp-tool, sb_unlink-mcp-tool]
  affects: [engine/mcp_server.py, tests/test_mcp.py]
tech_stack:
  added: []
  patterns: [INSERT OR IGNORE idempotency, optional rel_type DELETE filter]
key_files:
  created: []
  modified:
    - engine/mcp_server.py
    - tests/test_mcp.py
decisions:
  - "[28-04] sb_link uses source_path/target_path params matching relationships table column names; rel_type defaults to 'link'"
  - "[28-04] sb_unlink accepts optional rel_type — None removes all links between pair; absent pair is no-op (no rowcount check needed)"
  - "[28-04] Implementation was already committed in 478f2c5 (feat 28-02) by linter pre-seeding; tests added this session confirmed all 5 pass"
metrics:
  duration: "8 min"
  completed_date: "2026-03-19"
  tasks_completed: 1
  files_changed: 2
---

# Phase 28 Plan 04: sb_link and sb_unlink MCP Tools Summary

Two new MCP tools for explicit directional relationship management — `sb_link` (idempotent INSERT OR IGNORE) and `sb_unlink` (DELETE with optional rel_type filter, no-op on absent pair) — both DB-only, no note body edits.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement sb_link and sb_unlink (TDD) | 478f2c5 | engine/mcp_server.py, tests/test_mcp.py |

## What Was Built

### sb_link

```python
@mcp.tool()
def sb_link(source_path: str, target_path: str, rel_type: str = "link") -> dict:
```

- Inserts a row into the `relationships` table using `INSERT OR IGNORE` for idempotency.
- Returns `{"linked": True, "source": ..., "target": ..., "rel_type": ...}`.
- No file system writes — DB-only.

### sb_unlink

```python
@mcp.tool()
def sb_unlink(source_path: str, target_path: str, rel_type: str | None = None) -> dict:
```

- Deletes from `relationships` by source+target, optionally filtered by rel_type.
- Absent pair is a no-op — returns success without raising.
- Returns `{"unlinked": True, "source": ..., "target": ...}`.

## Test Coverage (5 tests, all passing)

| Test | Behavior |
|------|----------|
| test_sb_link_creates_relationship | Creates row with default rel_type='link' |
| test_sb_link_custom_rel_type | Stores custom rel_type='references' |
| test_sb_link_idempotent | Two calls → one row (INSERT OR IGNORE) |
| test_sb_unlink_removes | Link then unlink → table empty |
| test_sb_unlink_absent_is_noop | Unlink non-existent pair → success, no error |

## Verification

```
uv run pytest tests/test_mcp.py -q -k "sb_link or sb_unlink"
5 passed in <1s

uv run pytest tests/ --ignore=tests/test_gui.py
387 passed, 1 skipped, 9 xfailed, 35 xpassed
```

## Deviations from Plan

### Deviation: Implementation pre-committed in 478f2c5

- **Found during:** Commit step
- **Issue:** The linter-helper had pre-seeded `sb_link` and `sb_unlink` implementations alongside `sb_capture_smart` (plan 28-02) in commit `478f2c5`. The plan 28-04 implementation was already in HEAD before this session began.
- **Resolution:** This session added the 5 TDD tests (RED→GREEN cycle confirmed), removed duplicate function definitions the linter created, and verified the full suite passes. The net state is correct — single definitions, 5 passing tests.
- **Files modified:** engine/mcp_server.py, tests/test_mcp.py

## Self-Check: PASSED

- engine/mcp_server.py: FOUND (2 function definitions: sb_link, sb_unlink)
- tests/test_mcp.py: FOUND (5 tests passing)
- Implementation commit: 478f2c5 — FOUND in git log
