---
phase: 43
slug: smart-capture-multi-pass-decomposer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none (uses defaults) |
| **Quick run command** | `uv run pytest tests/test_smart_capture.py tests/test_typeclassifier.py -x -q` |
| **Full suite command** | delegate to user: `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (quick), ~30 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_smart_capture.py tests/test_typeclassifier.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/test_decomposer.py tests/test_smart_capture.py tests/test_typeclassifier.py -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green (delegate to user)
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 43-01-W0 | 01 | 0 | Wave 0 | unit | `uv run pytest tests/test_decomposer.py -x -q` | ❌ W0 | ⬜ pending |
| 43-01-P1 | 01 | 1 | Pass 1 entities | unit | `uv run pytest tests/test_decomposer.py::TestPass1 -x -q` | ❌ W0 | ⬜ pending |
| 43-01-P2 | 01 | 1 | Pass 2 URL extraction | unit | `uv run pytest tests/test_decomposer.py::TestPass2 -x -q` | ❌ W0 | ⬜ pending |
| 43-01-P3 | 01 | 1 | Pass 3 classify + conversation signal | unit | `uv run pytest tests/test_decomposer.py::TestPass3 tests/test_decomposer.py::TestConversationSignal -x -q` | ❌ W0 | ⬜ pending |
| 43-01-P4 | 01 | 1 | Pass 4 keyword + custom markers | unit | `uv run pytest tests/test_decomposer.py::TestPass4 tests/test_decomposer.py::TestCustomMarkers -x -q` | ❌ W0 | ⬜ pending |
| 43-01-P5 | 01 | 1 | Pass 5 assembly | unit | `uv run pytest tests/test_decomposer.py::TestPass5 -x -q` | ❌ W0 | ⬜ pending |
| 43-02-TC | 02 | 1 | typeclassifier URL override fix | unit | `uv run pytest tests/test_typeclassifier.py -x -q` | ✅ needs update | ⬜ pending |
| 43-03-CW | 03 | 2 | Caller wiring (api.py + mcp_server.py) | integration | `uv run pytest tests/test_smart_capture.py -x -q` | ✅ needs migration | ⬜ pending |
| 43-03-PAR | 03 | 2 | GUI/MCP parity (person stubs) | integration | `uv run pytest tests/test_smart_capture.py::TestGuiMcpParity -x -q` | ❌ W0 | ⬜ pending |
| 43-04-GUI | 04 | 3 | GUI settings panel (markers) | manual | N/A — Playwright on host | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_decomposer.py` — new test file covering all 5 passes and `DecomposedResult` shape (including `TestPass1`, `TestPass2`, `TestPass3`, `TestConversationSignal`, `TestPass4`, `TestCustomMarkers`, `TestPass5`)
- [ ] `tests/test_typeclassifier.py` — update `test_url_gives_link` to reflect new URL behaviour (meeting note with Zoom URL → classifies as "meeting", not "link")
- [ ] `tests/test_smart_capture.py` — migrate `TestSegmentStructuralMarkers` imports from `segment_blob` to `decompose`; add `TestGuiMcpParity` stub

*Note: `test_smart_capture_golden_path` is a pre-existing failure (Phase 45 tracks fix). Mark with `@pytest.mark.xfail` in Wave 0 — do not attempt to fix in Phase 43.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GUI settings panel renders markers | D-10 | Requires running frontend + sb-api; Playwright on host only | Load Settings modal → verify "Capture" section shows marker chips; add custom marker → save → reload → verify persisted |
| Meeting note with Zoom URL → 2 captured notes | D-04/D-06 | End-to-end capture flow through GUI | Submit meeting note with embedded Zoom URL via Smart Capture modal → verify "Saved 2 notes: meeting + link" in result |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
