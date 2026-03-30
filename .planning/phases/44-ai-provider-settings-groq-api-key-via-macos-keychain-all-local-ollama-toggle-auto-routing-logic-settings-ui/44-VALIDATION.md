---
phase: 44
slug: ai-provider-settings-groq-api-key-via-macos-keychain-all-local-ollama-toggle-auto-routing-logic-settings-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7+ |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_adapters.py tests/test_router.py -x -q` |
| **Full suite command** | `uv run pytest tests/test_adapters.py tests/test_router.py tests/test_api.py tests/test_config_loader.py -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_adapters.py tests/test_router.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_adapters.py tests/test_router.py tests/test_api.py tests/test_config_loader.py -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01 | 01 | 0 | D-01/D-02 | unit | `uv run pytest tests/test_adapters.py -k groq -x` | ❌ W0 | ⬜ pending |
| 44-02 | 01 | 0 | D-04/D-05 | unit | `uv run pytest tests/test_router.py -k all_local -x` | ❌ W0 | ⬜ pending |
| 44-03 | 01 | 0 | D-08/D-09 | unit | `uv run pytest tests/test_api.py -k groq_config -x` | ❌ W0 | ⬜ pending |
| 44-04 | 02 | 1 | D-01 | unit | `uv run pytest tests/test_adapters.py -k groq -x` | ❌ W0 | ⬜ pending |
| 44-05 | 02 | 1 | D-02 | unit | `uv run pytest tests/test_adapters.py -k groq_keychain -x` | ❌ W0 | ⬜ pending |
| 44-06 | 02 | 1 | D-11 | unit | `uv run pytest tests/test_adapters.py -k groq_fallback -x` | ❌ W0 | ⬜ pending |
| 44-07 | 03 | 1 | D-04/D-05 | unit | `uv run pytest tests/test_router.py -k all_local -x` | ❌ W0 | ⬜ pending |
| 44-08 | 03 | 1 | D-07 | unit | `uv run pytest tests/test_config_loader.py -x -q` | ✅ existing | ⬜ pending |
| 44-09 | 04 | 2 | D-08 | unit | `uv run pytest tests/test_api.py -k groq_config -x` | ❌ W0 | ⬜ pending |
| 44-10 | 04 | 2 | D-09 | unit | `uv run pytest tests/test_api.py -k test_groq_connection -x` | ❌ W0 | ⬜ pending |
| 44-11 | 04 | 2 | D-12 | unit | `uv run pytest tests/test_api.py -k ask_brain_provider -x` | ❌ W0 | ⬜ pending |
| 44-12 | 05 | 3 | D-10 | manual | Playwright: open Settings, verify AI Provider section renders | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_adapters.py` — append GroqAdapter test stubs (D-01, D-02, D-11)
- [ ] `tests/test_router.py` — append all_local and groq feature routing test stubs (D-04, D-05)
- [ ] `tests/test_api.py` — append Keychain endpoint test stubs with mocked `keyring` (D-08, D-09, D-12)
- [ ] `tests/conftest.py` — add `mock_keyring` fixture: patch `keyring.get_password`, `keyring.set_password`, `keyring.delete_password`

*All target test files already exist — append new test functions, no new files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Settings UI — AI Provider section renders correctly | D-10 | Requires browser/Playwright, visual verification | Open Settings modal, confirm "AI Provider" section appears with key input, all-local toggle, feature toggles |
| Groq key save → auto connectivity test → shows ✓ Connected | D-09/D-10 | Requires real Groq key or Playwright mock | Enter key, Save, confirm spinner then result badge appears |
| All-local ON → feature toggles greyed out | D-10 | Visual state, Playwright | Toggle all-local ON, confirm 4 feature toggles show opacity-50 |
| Fallback toast appears when Groq unavailable | D-12 | Requires simulated Groq failure | Mock Groq endpoint to fail, trigger Ask Brain, confirm amber toast |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
