---
phase: 57
slug: memory-consolidation-and-enrichment
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_enrich.py tests/test_consolidate.py tests/test_capture_similarity.py tests/test_mcp_consolidation.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run the plan's own `<verify><automated>` command
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 57-01-01 | 01 | 1 | consolidation_queue + enrich_note() | unit | `uv run pytest tests/test_enrich.py -x` | ❌ (plan creates) | ⬜ pending |
| 57-02-01 | 02 | 2 | merge_notes() upgrade | unit | `uv run pytest tests/test_brain_health.py -k "merge" -x` | ✅ (extends existing) | ⬜ pending |
| 57-03-01 | 03 | 1 | capture-time similarity hints | integration | `uv run pytest tests/test_capture_similarity.py -x` | ❌ (plan creates) | ⬜ pending |
| 57-04-01 | 04 | 2 | nightly enrichment + stale + backlink | unit | `uv run pytest tests/test_consolidate.py -x` | ❌ (plan creates) | ⬜ pending |
| 57-05-01 | 05 | 3 | sb_enrich MCP tool | integration | `uv run pytest tests/test_mcp_consolidation.py -k "enrich" -x` | ❌ (plan creates) | ⬜ pending |
| 57-05-02 | 05 | 3 | sb_consolidation_review MCP tool | integration | `uv run pytest tests/test_mcp_consolidation.py -k "review" -x` | ❌ (plan creates) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*No Wave 0 needed — each plan creates its own test file alongside implementation.*
*Existing test infrastructure (conftest.py, brain fixtures) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Ollama enrichment quality | enrich_note AI output | AI output non-deterministic | Review enriched note body for coherence and tag accuracy |
| Similarity hint UX | capture-time hints | Requires MCP client context | Capture a note via Claude, check hint appears in response |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
