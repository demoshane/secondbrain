---
phase: 29
slug: add-link-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_link_capture.py -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_link_capture.py -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 0 | LINK-01..04 | unit stub | `uv run pytest tests/test_link_capture.py -q` | ❌ W0 | ⬜ pending |
| 29-02-01 | 02 | 1 | LINK-01,02 | unit | `uv run pytest tests/test_link_capture.py::test_fetch_metadata_returns_title tests/test_link_capture.py::test_fetch_metadata_fallback_on_error -q` | ❌ W0 | ⬜ pending |
| 29-02-02 | 02 | 1 | LINK-03 | unit | `uv run pytest tests/test_link_capture.py::test_url_column_exists -q && uv run pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 29-03-01 | 03 | 2 | LINK-03,05 | unit | `uv run pytest tests/test_link_capture.py::test_sb_capture_link_registered tests/test_link_capture.py::test_capture_link_duplicate_warn -q` | ❌ W0 | ⬜ pending |
| 29-03-02 | 03 | 2 | LINK-04,05 | unit | `uv run pytest tests/test_link_capture.py::test_links_api_returns_list -q && uv run pytest tests/ -q` | ❌ W0 | ⬜ pending |
| 29-04-01 | 04 | 3 | LINK-06 | build | `cd frontend && npm run build` | n/a | ⬜ pending |
| 29-04-02 | 04 | 3 | LINK-06,07 | build | `cd frontend && npm run build` | n/a | ⬜ pending |
| 29-04-03 | 04 | 3 | LINK-06,07 | manual | n/a — pywebview render | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_link_capture.py` — stubs for all link capture behaviors
- [ ] DB migration stub test (url column exists)
- [ ] MCP tool stub test (sb_capture_link registered)

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LinksPage renders in GUI | link-capture | pywebview WKWebView — no headless DOM | Launch sb-gui, navigate to Links tab, verify list renders |
| "Visit Link" opens browser | link-capture | window.open / anchor behavior in WKWebView env | Click link, verify external browser opens |
| Link appears after MCP capture | link-capture | Full E2E MCP → DB → GUI | Use sb_capture_link via MCP, reload GUI, verify entry |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
