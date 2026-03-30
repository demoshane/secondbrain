---
phase: 46
slug: universal-capture-enrichment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_capture.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_capture.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | universal-enrichment | unit | `uv run pytest tests/test_capture.py -x -q -k "enrich"` | ✅ exists | ⬜ pending |
| 46-01-02 | 01 | 1 | universal-enrichment | unit | `uv run pytest tests/test_capture.py -x -q -k "stub"` | ✅ exists | ⬜ pending |
| 46-01-03 | 01 | 1 | universal-enrichment | unit | `uv run pytest tests/test_capture.py -x -q -k "action"` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. `tests/test_capture.py` with `TestPersonStubCreation` class already exists.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end: capture via `sb_capture` MCP → person stub appears in brain | integration | Requires running MCP server | Use Claude Desktop, capture a note mentioning a real person name, then search for that name |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
