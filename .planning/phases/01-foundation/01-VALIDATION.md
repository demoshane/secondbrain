---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | FOUND-01..12 | setup | `uv pip install pytest pytest-cov` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 1 | FOUND-01 | smoke | `pytest tests/test_devcontainer.py::test_remote_user -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 1 | FOUND-09 | smoke | `pytest tests/test_gitignore.py::test_env_host_ignored -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 1 | FOUND-08 | integration | `pytest tests/test_precommit.py::test_blocks_api_key -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | FOUND-03 | unit | `pytest tests/test_init_brain.py::test_creates_subdirs -x` | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | FOUND-04 | unit | `pytest tests/test_db.py::test_schema_complete -x` | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | FOUND-05 | unit | `pytest tests/test_init_brain.py::test_drive_validation_blocks_on_unwritable -x` | ❌ W0 | ⬜ pending |
| 1-03-04 | 03 | 2 | FOUND-06 | unit | `pytest tests/test_init_brain.py::test_vscode_settings_generated -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 2 | FOUND-07 | unit | `pytest tests/test_reindex.py::test_reindex_inserts_all_markdown -x` | ❌ W0 | ⬜ pending |
| 1-05-01 | 05 | 3 | FOUND-10 | unit | `pytest tests/test_bootstrap.py::test_reports_pass_fail_per_check -x` | ❌ W0 | ⬜ pending |
| 1-05-02 | 05 | 3 | FOUND-12 | smoke | `pytest tests/test_paths.py::test_no_hardcoded_separators -x` | ❌ W0 | ⬜ pending |
| 1-06-01 | 06 | 3 | FOUND-02 | manual | See manual verification table below | manual-only | ⬜ pending |
| 1-06-02 | 06 | 3 | FOUND-11 | manual | See manual verification table below | manual-only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures (tmp_path brain root, in-memory SQLite connection)
- [ ] `tests/test_devcontainer.py` — parses devcontainer.json, checks remoteUser and mounts
- [ ] `tests/test_db.py` — schema init, idempotency, FTS5 triggers
- [ ] `tests/test_init_brain.py` — subdir creation, Drive validation, .vscode/settings.json
- [ ] `tests/test_reindex.py` — markdown walk, FTS5 insert
- [ ] `tests/test_precommit.py` — detect-secrets integration test
- [ ] `tests/test_gitignore.py` — .gitignore coverage check
- [ ] `tests/test_bootstrap.py` — bootstrap.py check reporting
- [ ] `tests/test_paths.py` — static analysis: no `os.path.join` or hardcoded `/workspace/brain` outside paths.py
- [ ] `pyproject.toml` — pytest config section
- [ ] Framework install: `uv pip install pytest pytest-cov`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `${localEnv:HOME}` brain mount works on macOS | FOUND-02 | Requires running container on physical host | Open devcontainer on macOS; verify `~/SecondBrain` appears at `/workspace/brain` inside container with correct ownership |
| Windows WSL2 brain mount (with warning) | FOUND-02 | Requires Windows+Docker Desktop — not automatable in CI | Open devcontainer on Windows; verify bootstrap.py shows warning about WSL2 HOME expansion; confirm mount path |
| Fresh install end-to-end | FOUND-11 | Requires clean machine state | Clone repo fresh → place `.env.host` outside `~/SecondBrain/` → run `bootstrap.py --dev` → run `/sb-init` → verify all checks green |
| File written in container visible on host | success criteria #5 | Requires live bind-mount test | Write file inside container at `/workspace/brain/test.md` → verify visible at `~/SecondBrain/test.md` on host with correct ownership |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
