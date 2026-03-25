---
status: complete
phase: 37-housekeeping
source: [37-01-SUMMARY.md, 37-02-SUMMARY.md, 37-03-SUMMARY.md, 37-04-SUMMARY.md, 37-08-SUMMARY.md]
started: 2026-03-25T22:40:00Z
updated: 2026-03-25T22:40:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

## Current Test

[testing complete]

## Tests

### 1. People chips in NoteViewer — add a person
expected: Open any note in the GUI. Below the tag chips row, a people chips row (data-testid="people-chips") should be visible. Clicking "+" opens a person autocomplete input. Typing a person name shows matching suggestions. Selecting one adds a chip labelled with the person's name. The chip persists after navigating away and reopening the note.
result: pass

### 2. Action item creation from person detail
expected: Navigate to People page → click any person row → in the right-hand detail panel, find the "Open Actions" section. An inline text input and "Add" button should appear above the action item list. Type a task and click Add — the new action item appears in the list immediately, pre-assigned to that person.
result: issue
reported: "Calendar doesn't work; when I add an assignee, the action item disappears completely and cannot be seen in the person's Open Actions section"
severity: major

### 3. Delete modal shows impact preview
expected: Open any note that has associated action items or relationships. Click the trash icon (delete-btn). The Delete Note modal should appear showing an "Impact" block with counts: "Action items: N · Relationships: N · Mentioned in: N notes". A loading skeleton is shown while the counts are fetching. Notes with zero impact show no impact block.
result: pass

### 4. Drive sync health check
expected: Run `sb-health` in terminal (or check the /brain-health API endpoint). Output should include a "drive_sync" section with one of three statuses: "ok" (Drive running and brain folder synced), "not_running" (Drive installed but not running), or "not_installed" (Drive app not found). No crash or missing key.
result: issue
reported: "sb-health produces no drive_sync output — section entirely absent"
severity: major

### 5. sb_recap MCP returns real recap content
expected: Via Claude Desktop or MCP client, call `sb_recap` with no arguments. It should return a real activity recap — recent notes, themes, action items — NOT the old "No recap available for this context." stub. Content should reflect recent brain activity.
result: issue
reported: "sb_recap timed out — server didn't respond within 60 seconds"
severity: major

## Summary

total: 5
passed: 2
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "New action item created from person detail appears immediately in Open Actions list, assigned to that person"
  status: failed
  reason: "User reported: action item disappears after adding assignee; not visible in person's Open Actions section. Calendar widget also broken."
  severity: major
  test: 2
  artifacts:
    - "frontend/src/components/PeoplePage.tsx:56-59"
    - "frontend/src/components/ActionItemList.tsx:10"
  root_cause: |
    PeoplePage.tsx fetches peopleNotes from GET /notes (50-item limit). People notes created weeks ago
    won't be in the 50-item window, so peopleNotes ends up missing most persons. ActionItemList receives
    people={peopleNotes} for its assignee dropdown. When user assigns to someone not in the 50-item
    window, assignTo() updates assignee_path to the selected person, then reloadActions queries
    WHERE assignee_path = originalPerson → 0 results → item appears to disappear.
    Fix: derive peopleNotes from /persons API response (which has all persons) instead of /notes.
  missing: []

- truth: "sb-health outputs a drive_sync status line (ok / not_running / not_installed)"
  status: failed
  reason: "sb-health produces no drive_sync output — check_drive_sync() added to brain_health.py but not wired into the sb-health CLI display"
  severity: major
  test: 4
  artifacts:
    - "engine/health.py:186"
  root_cause: |
    engine/health.py has its own CHECKS list that drives the display loop. check_drive_sync() was
    added to engine/brain_health.py but never added to the CHECKS list in engine/health.py.
    Fix: add a wrapper in health.py that calls brain_health.check_drive_sync() and append it to CHECKS.
  missing: []

- truth: "sb_recap MCP tool returns real recap content within timeout"
  status: failed
  reason: "sb_recap timed out — server didn't respond within 60 seconds"
  severity: major
  test: 5
  artifacts:
    - "engine/adapters/claude_adapter.py:45-50"
    - "engine/mcp_server.py:600"
    - "engine/intelligence.py:584-594"
  root_cause: |
    Three compounding issues: (1) subprocess.run(timeout=60) in claude_adapter.py blocks for up to 60s
    per adapter.generate() call; (2) generate_recap_on_demand() makes 2 adapter.generate() calls
    (public + PII) = 120s wall-clock ceiling; (3) _retry_call in mcp_server.py wraps _do_recap with
    up to 4 retry attempts = 240s worst case. Any one alone exceeds the 60s MCP client timeout.
    Fix: reduce subprocess timeout to 30s, add total budget check to skip PII call if public took too
    long, and remove _retry_call wrapper around _do_recap (retry is wrong for AI inference).
  missing: []
