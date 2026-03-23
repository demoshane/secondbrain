---
phase: 36
slug: chrome-extension-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | backend: /ping endpoint | unit | `uv run pytest tests/test_api.py -q -k ping` | ❌ W0 | ⬜ pending |
| 36-01-02 | 01 | 1 | backend: CORS chrome-extension | unit | `uv run pytest tests/test_api.py -q -k cors` | ❌ W0 | ⬜ pending |
| 36-01-03 | 01 | 1 | backend: source_url param | unit | `uv run pytest tests/test_api.py -q -k source_url` | ❌ W0 | ⬜ pending |
| 36-01-04 | 01 | 1 | extension scaffold | manual | chrome://extensions load unpacked | N/A | ⬜ pending |
| 36-02-01 | 02 | 2 | Gmail content script | manual | Load on mail.google.com, verify button injected | N/A | ⬜ pending |
| 36-03-01 | 03 | 3 | GUI install button | unit | `uv run pytest tests/test_api.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — add stubs for `/ping`, CORS `chrome-extension://*`, `source_url` param on `/capture` and `/smart-capture`

*Existing infrastructure covers most backend requirements; Wave 0 adds extension-specific test stubs only.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extension popup opens on icon click | D-04 | Requires Chrome browser | Load unpacked, click icon, verify popup renders |
| Context menu shows on right-click | D-02 | Requires Chrome browser | Right-click page, verify "Save to Brain" menu item |
| Full article extracted via Readability | D-06 | Requires live page | Navigate to article, capture, verify body in ~/SecondBrain |
| Gmail button injected in thread view | D-07 | Requires Gmail DOM | Open email thread, verify "Save to Brain" button |
| Gmail context menu works | D-07 | Requires Gmail DOM | Right-click in thread, verify menu item |
| Capture history shows last 10 | D-11 | Requires localStorage | Perform 3+ captures, open popup, verify history list |
| Options page saves sb-api URL | D-12 | Requires browser storage | Open options, change URL, verify saved |
| Extension icon badge on api down | D-09 | Requires Chrome badge API | Stop sb-api, verify red badge on icon |
| setup.sh prompts for extension install | D-16 | Requires terminal interaction | Run setup.sh, verify Chrome instructions displayed |
| Intelligence page install button | D-17 | Requires GUI | Open Intelligence page, verify button present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
