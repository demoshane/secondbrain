---
phase: 38
slug: scale-architecture-100k-notes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -q -x` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -q -x`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 0 | SCALE-01 | unit | `uv run pytest tests/test_ann_index.py -q` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 1 | SCALE-06 | unit | `uv run pytest tests/test_chunks.py -q` | ❌ W0 | ⬜ pending |
| 38-03-01 | 03 | 1 | SCALE-02 | unit | `uv run pytest tests/test_reindex.py -q` | ✅ | ⬜ pending |
| 38-04-01 | 04 | 1 | SCALE-04 | unit | `uv run pytest tests/test_audit_rotation.py -q` | ❌ W0 | ⬜ pending |
| 38-05-01 | 05 | 2 | SCALE-05 | unit | `uv run pytest tests/test_tiered_storage.py -q` | ❌ W0 | ⬜ pending |
| 38-06-01 | 06 | 2 | SCALE-07 | unit | `uv run pytest tests/test_summarization.py -q` | ❌ W0 | ⬜ pending |
| 38-07-01 | 07 | 2 | SCALE-08 | unit | `uv run pytest tests/test_consolidation.py -q` | ❌ W0 | ⬜ pending |
| 38-08-01 | 08 | 2 | SCALE-03 | unit | `uv run pytest tests/test_backup.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ann_index.py` — stubs for SCALE-01 (hnswlib index build/query/rebuild)
- [ ] `tests/test_chunks.py` — stubs for SCALE-06 (chunk embedding, excerpt search)
- [ ] `tests/test_audit_rotation.py` — stubs for SCALE-04 (rotation threshold, archive)
- [ ] `tests/test_tiered_storage.py` — stubs for SCALE-05 (tier move, DB transaction)
- [ ] `tests/test_summarization.py` — stubs for SCALE-07 (summarization trigger, storage)
- [ ] `tests/test_consolidation.py` — stubs for SCALE-08 (candidate surfacing, merge)
- [ ] `tests/test_backup.py` — stubs for SCALE-03 (encrypt/decrypt, restore)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drive-synced backup visible in Google Drive | SCALE-03 | Requires configured Drive mount | Run `sb-backup`, verify file appears in `~/SecondBrain/.backup/` and Drive sync occurs |
| hnswlib ANN search latency at scale | SCALE-01 | No 100K-note test fixture | Load-test with synthetic notes, measure p95 query latency |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
