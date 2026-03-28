---
phase: 39-codebase-review
plan: 13
status: complete
---

## What was done

Created 4 new test files and 1 additional MCP test to close COV-06 through COV-10:

| File | Tests | Coverage target |
|------|-------|-----------------|
| `tests/test_attachments.py` | 6 | COV-06: attachments.py |
| `tests/test_merge_cli.py` | 5 | COV-07: merge_cli.py |
| `tests/test_config_loader.py` | 5 | COV-08: config_loader.py |
| `tests/test_ratelimit.py` | 5 | COV-09: ratelimit.py |
| `tests/test_mcp.py` (+1) | 1 | COV-10: audit_log via sb_capture |

All 24 new tests pass. Full targeted run: `24 passed in 3.33s`.

## Key decisions

- `test_attachments.py`: uses `attachment_brain` fixture with monkeypatched DB_PATH — matches established pattern from conftest.py. Tests both DB functions (`save_attachment`, `list_attachments`) and the suppress-set helpers.
- `test_merge_cli.py`: tests `merge_notes()` directly (the real logic) rather than mocking through `merge_duplicates_main`. Also tests `merge_duplicates_main` with no-candidates mock for the CLI path.
- `test_config_loader.py`: tests default fallback, TOML parse, and critical key presence. Used `write_bytes` with binary TOML content for tomllib compatibility.
- `test_ratelimit.py`: uses `monkeypatch` on `time.monotonic` to simulate window expiry — avoids real `time.sleep` in tests.
- Audit log test (`test_capture_creates_audit_log_entry`): uses `isolated_mcp_brain` fixture, verifies `event_type='mcp_capture'` row and slug in `note_path`.
