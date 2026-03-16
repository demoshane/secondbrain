---
phase: 14
slug: embedding-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-15
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 7.0 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_embeddings.py -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_embeddings.py -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | EMBED-01 | unit | `pytest tests/test_embeddings.py::test_reindex_generates_embeddings -x` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 0 | EMBED-01 | unit | `pytest tests/test_embeddings.py::test_reindex_full_flag -x` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | EMBED-02 | unit (mock) | `pytest tests/test_embeddings.py::test_embed_no_network_call -x` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | EMBED-03 | unit | `pytest tests/test_embeddings.py::test_reindex_incremental_skips_unchanged -x` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 1 | EMBED-03 | unit | `pytest tests/test_embeddings.py::test_reindex_incremental_reembeds_changed -x` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 1 | EMBED-04 | unit | `pytest tests/test_embeddings.py::test_forget_cascades_to_embeddings -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_embeddings.py` — stubs for EMBED-01, EMBED-02, EMBED-03, EMBED-04
- [ ] `conftest.py` update — add `vec_conn` fixture (sqlite-vec loaded) for future Phase 16 tests
- [ ] `uv add sentence-transformers sqlite-vec` — neither in `pyproject.toml` yet

*Test strategy: mock `engine.embeddings._get_model` returning a mock `.encode()` yielding `np.zeros((N, 384), dtype=np.float32)` — avoids 90MB model download in CI.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sqlite_vec` extension loads on this macOS Python build | EMBED-01 | Build-environment-specific; Wave 0 probe task handles it | Run `python -c "import sqlite_vec; print('ok')"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
