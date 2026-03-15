---
phase: 3
slug: ai-layer
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `uv run pytest tests/test_pii.py tests/test_router.py tests/test_enrichment.py tests/test_subagent.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds (mocked adapters) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_pii.py tests/test_router.py tests/test_enrichment.py tests/test_subagent.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-00-01 | 00 | 0 | AI-01–AI-10, CAP-06 | stub | `uv run pytest tests/test_pii.py tests/test_router.py tests/test_enrichment.py tests/test_subagent.py --collect-only` | ✅ | ✅ green |
| 3-01-01 | 01 | 1 | AI-01,AI-02 | unit | `uv run pytest tests/test_pii.py -x -q` | ✅ | ✅ green |
| 3-02-01 | 02 | 1 | AI-03,AI-04,AI-05 | unit | `uv run pytest tests/test_router.py -x -q` | ✅ | ✅ green |
| 3-03-01 | 03 | 2 | AI-06,AI-07,AI-08 | unit+mock | `uv run pytest tests/test_enrichment.py -x -q` | ✅ | ✅ green |
| 3-04-01 | 04 | 3 | AI-09,AI-10,CAP-06 | unit+integration | `uv run pytest tests/test_subagent.py -x -q` | ✅ | ✅ green |
| 3-05-01 | 05 | 4 | all | manual | N/A (checkpoint) | N/A | manual-only |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_pii.py` — stubs for AI-01, AI-02 (PII classifier)
- [x] `tests/test_router.py` — stubs for AI-03, AI-04, AI-05 (ModelRouter + config)
- [x] `tests/test_enrichment.py` — stubs for AI-06, AI-07, AI-08 (proactive questioning)
- [x] `tests/test_subagent.py` — stubs for AI-09, AI-10, CAP-06 (subagent + skill file)
- [x] `tests/conftest.py` — extend with mock_claude_adapter, mock_ollama_adapter fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zero outbound Anthropic calls on PII note | AI-02 | Requires network monitoring inside container | `tcpdump` or mock + assert no call to api.anthropic.com |
| `claude` CLI on PATH in DevContainer | AI-09 | Binary presence can't be mocked | Run `which claude` inside container |
| Subagent invokable from Claude Code | AI-10 | Requires live Claude Code session | Open Claude Code, run `/sb-capture`, confirm result |
| Ollama host.docker.internal reachable | AI-03 | Requires Ollama running on host | `curl http://host.docker.internal:11434/api/tags` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (automated coverage confirmed; live-env manual items annotated manual-only — not blocking nyquist sign-off)
