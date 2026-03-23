---
phase: 36
slug: chrome-extension-capture
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-23
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + manual browser verification (extension) |
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/ -q -x` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 36-01-T1 | 01 | 1 | backend: /ping, CORS, source_url/source_type | unit | `uv run pytest tests/test_api.py -x -q -k "test_ping or test_cors or test_smart_capture_source_url or test_create_note_source_url"` | pending |
| 36-02-T1 | 02 | 1 | extension scaffold: manifest, vendor, options | file-exists | `test -f chrome-extension/manifest.json && python3 -c "import json; json.load(open('chrome-extension/manifest.json'))" && test -f chrome-extension/lib/Readability.js && test -f chrome-extension/options.html && echo PASS` | pending |
| 36-02-T2 | 02 | 1 | core capture: background, content, popup | file-grep | `grep -q "contextMenus.create" chrome-extension/background.js && grep -q "extract-article" chrome-extension/content.js && grep -q "capture-form" chrome-extension/popup.html && echo PASS` | pending |
| 36-03-T1 | 03 | 2 | Gmail: button injection, thread extraction, fallback | file-grep | `grep -q "sb-gmail-btn" chrome-extension/content.js && grep -q "capture-gmail" chrome-extension/background.js && grep -q "showInPageNotification" chrome-extension/content.js && echo PASS` | pending |
| 36-04-T1 | 04 | 3 | badge polling, capture history, status | file-grep | `grep -q "setBadgeText" chrome-extension/background.js && grep -q "captureHistory" chrome-extension/popup.js && grep -q "alarms" chrome-extension/manifest.json && echo PASS` | pending |
| 36-04-T2 | 04 | 3 | install UX: setup.sh + Intelligence page | file-grep | `grep -q "chrome-extension" setup.sh && grep -q "Chrome Extension" frontend/src/components/IntelligencePage.tsx && echo PASS` | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Wave 0 stubs are NOT needed for this phase:
- Plan 36-01 writes tests inline alongside implementation (not TDD -- `tdd="true"` removed). Tests are created in the same task as the code they verify.
- Plans 36-02 through 36-04 are Chrome extension files verified by file-existence and grep checks, not pytest. No Wave 0 stub infrastructure needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extension popup opens on icon click | D-04 | Requires Chrome browser | Load unpacked, click icon, verify popup renders |
| Context menu shows on right-click | D-02 | Requires Chrome browser | Right-click page, verify "Save to Brain" menu item |
| Full article extracted via Readability | D-06 | Requires live page | Navigate to article, capture, verify body in ~/SecondBrain |
| Gmail button injected in thread view | D-07 | Requires Gmail DOM | Open email thread, verify "Save to Brain" button |
| Gmail button fallback notification | D-07 | Requires Gmail DOM | If openPopup fails, verify in-page notification appears |
| Gmail context menu works | D-07 | Requires Gmail DOM | Right-click in thread, verify menu item |
| Capture history shows last 10 | D-11 | Requires localStorage | Perform 3+ captures, open popup, verify history list |
| Options page saves sb-api URL | D-12 | Requires browser storage | Open options, change URL, verify saved |
| Extension icon badge on api down | D-09 | Requires Chrome badge API | Stop sb-api, verify red badge on icon |
| setup.sh prompts for extension install | D-16 | Requires terminal interaction | Run setup.sh, verify Chrome instructions displayed |
| Intelligence page install button | D-17 | Requires GUI | Open Intelligence page, verify button and inline instructions |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 not needed (no TDD tasks, extension verified by file checks)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
