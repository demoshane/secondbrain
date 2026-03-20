---
phase: 25
slug: file-capture-batch-capture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 25 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, pyproject.toml) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_api_upload.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_api_upload.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 25-xx-01 | 01 | 0 | GUIF-01 | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_saves_file -x` | ❌ W0 | ⬜ pending |
| 25-xx-02 | 01 | 0 | GUIF-01 | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_inserts_attachment_row -x` | ❌ W0 | ⬜ pending |
| 25-xx-03 | 01 | 0 | GUIF-01 | unit | `uv run pytest tests/test_api_upload.py::TestFileUpload::test_upload_rejects_executable -x` | ❌ W0 | ⬜ pending |
| 25-xx-04 | 01 | 0 | GUIF-01 | unit | `uv run pytest tests/test_api_upload.py::TestAttachmentsList::test_list_attachments -x` | ❌ W0 | ⬜ pending |
| 25-xx-05 | 02 | 0 | ENGL-01 | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_captures_unindexed -x` | ❌ W0 | ⬜ pending |
| 25-xx-06 | 02 | 0 | ENGL-01 | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_skips_indexed -x` | ❌ W0 | ⬜ pending |
| 25-xx-07 | 02 | 0 | ENGL-01 | unit | `uv run pytest tests/test_api_upload.py::TestBatchCapture::test_batch_returns_structured_result -x` | ❌ W0 | ⬜ pending |
| 25-xx-08 | 01 | 0 | GUIF-01+ENGL-01 | unit | `uv run pytest tests/test_note_watcher.py::TestWatcherDedup -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api_upload.py` — stubs for GUIF-01 and ENGL-01 API endpoints (upload, attachments list, batch capture)
- [ ] `TestWatcherDedup` class in `tests/test_note_watcher.py` — covers upload dedup guard (file exists; class is new)

*Existing infrastructure (pytest, uv, Flask test client, monkeypatch BRAIN_PATH, tmp_path) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-and-drop file onto viewer area | GUIF-01 | DOM drag events not easily testable in Flask unit tests | Open GUI, drag a file onto `#viewer`, confirm upload toast and sidebar refresh |
| File upload button in sidebar toolbar triggers file picker | GUIF-01 | `<input type="file">` click interaction is browser-only | Open GUI, click upload button, confirm file dialog opens |
| Batch Capture button in sidebar triggers scan and sidebar refresh | ENGL-01 | SSE broadcast + sidebar DOM update is browser-only | Add .md files to brain dir, click Batch Capture, confirm sidebar updates |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
