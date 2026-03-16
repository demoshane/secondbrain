---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Intelligence + GUI Hub
status: completed
stopped_at: Completed 19-04-PLAN.md — Phase 19 MCP server human verification complete
last_updated: "2026-03-16T08:07:59.670Z"
last_activity: 2026-03-15 — 18-03 complete (human verification sign-off; all 11 GUI requirements approved)
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 23
  completed_plans: 23
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Zero-friction capture that surfaces the right context at the right moment
**Current focus:** Phase 18 — GUI Hub (COMPLETE)

## Current Position

Phase: 18 of 19 (GUI Hub — complete)
Plan: 18-03 (complete — final plan)
Status: Phase complete, milestone v2.0 complete
Last activity: 2026-03-15 — 18-03 complete (human verification sign-off; all 11 GUI requirements approved)

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 15 P01 | 206s | 2 tasks | 3 files |
| Phase 15 P02 | 18 | 3 tasks | 2 files |
| Phase 15 P03 | 6 | 3 tasks | 4 files |
| Phase 15 P04 | 8 | 2 tasks | 2 files |
| Phase 16 P01 | 4 | 2 tasks | 6 files |
| Phase 16 P02 | 8 | 2 tasks | 3 files |
| Phase 16 P03 | 5 | 2 tasks | 2 files |
| Phase 16 P04 | 196 | 2 tasks | 4 files |
| Phase 17 P00 | 85 | 2 tasks | 3 files |
| Phase 17 P01 | 240 | 1 tasks | 2 files |
| Phase 17 P02 | 8 | 1 tasks | 1 files |
| Phase 18-gui-hub P00 | 251 | 2 tasks | 4 files |
| Phase 18-gui-hub P01 | 446 | 2 tasks | 5 files |
| Phase 18-gui-hub P02 | 3 | 2 tasks | 6 files |
| Phase 18-gui-hub P03 | 5 | 2 tasks | 0 files |
| Phase 19-mcp-server P01 | 362 | 3 tasks | 5 files |
| Phase 19-mcp-server P02 | 25 | 2 tasks | 2 files |
| Phase 19-mcp-server P03 | 480 | 2 tasks | 3 files |
| Phase 19-mcp-server P04 | 10 | 2 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0 Roadmap]: pywebview 5.4 chosen over Tauri — PyTauri pre-1.0 (v0.8, Feb 2026); revisit when PyTauri hits 1.0
- [Phase 14]: Ollama is default embedding provider — fastembed/onnxruntime dropped Intel Mac x86_64 support; fastembed deferred until Apple Silicon migration
- [Phase 14]: Python pinned to 3.13 via .python-version — PyTorch/onnxruntime have no Python 3.14 wheels; revisit on M-chip
- [v2.0 Roadmap]: sentence-transformers + all-MiniLM-L6-v2 is primary embedding path; Ollama embeddings are optional GPU-enhanced fallback
- [v2.0 Roadmap]: Argon2id is the preferred KDF over PBKDF2 — decision to confirm at Phase 14 planning
- [v2.0 Roadmap]: Only `content_sensitivity: pii` Markdown files are Fernet-encrypted; all other notes remain plaintext (Drive diff/sync compatibility)
- [v2.0 Roadmap]: Proactive budget = one unsolicited offer per session; cooldown persisted in `~/.meta/intelligence_state.json`; vault gate = 20 notes minimum
- [v2.0 Roadmap]: GUI calls `engine/api.py` only — never imports `engine/` modules directly (C1 hard dependency)
- [Phase 15]: _router = None placeholder added to intelligence.py for mock patching; action_items DDL in both SCHEMA_SQL and separate migration function
- [Phase 15]: Used _RouterShim wrapping engine.router.get_adapter() — router.py exports bare function, not ModelRouter class
- [Phase 15]: Module-level imports for get_connection in intelligence.py so tests can patch engine.intelligence.get_connection
- [Phase 15]: intelligence.py was fully implemented in 15-02 session; Task 1 was a no-op verification pass
- [Phase 15]: search.py conn.close() ordering bug fixed — stale nudge now fires with open conn before final close
- [Phase 15]: INTL-10: check_connections() gated on budget_available() and consumes budget after firing — single-offer-per-day contract fully enforced across all proactive functions
- [Phase 16]: Wave 0 pattern: import non-existent symbol directly — ImportError/AttributeError is the RED signal for scaffold tests
- [Phase 16]: TestDigestFlag uses pytest.raises(SystemExit) — engine.read.main() takes no args yet; Plan 04 must update both flag and tests
- [Phase 16]: search_semantic returns [] when note_embeddings empty; search_hybrid falls back silently to FTS5 in that case
- [Phase 16]: main() accepts argv parameter for test injection — avoids sys.argv patching in unit tests
- [Phase 16]: conftest seeded_db seeds 100 note_embeddings rows with stub BLOBs so TestSemanticSearch can assert results > 0 without downloading models
- [Phase 16]: recap_entity returns string (not None) to satisfy test assertion; tagged people/tags query is authoritative source to prevent FTS false positives
- [Phase 16]: seeded_db fixture extended with alice PII notes so entity recap tests have data without real vault files
- [Phase 16]: conn=None guard added to generate_digest() so tests with None conn skip DB queries gracefully
- [Phase 16]: TestDigestPIIRouting fixed: monkeypatch engine.intelligence._router and seed in-memory DB with PII note
- [Phase 16]: write_digest_plist() wrapped in non-fatal try/except in install_native main() — binary may not be installed yet
- [Phase 17]: Import new symbols at module level — collection-level ImportError is the clearest RED signal (matches Phase 16 pattern)
- [Phase 17]: sb-api entry point added to pyproject.toml alongside other sb-* CLI commands
- [Phase 17]: list_actions(conn, done) added to intelligence.py — was missing, referenced in plan but not yet implemented
- [Phase 17]: sqlite3.Row row_factory set per-request since get_connection() returns plain connection without row_factory
- [Phase 17]: assert_drive_or_exit takes base_path kwarg (not home) to match test scaffold signature
- [Phase 17]: ollama_model_size_warning uses ollama Python SDK ollama.list() — not subprocess — to match test scaffold
- [Phase 17]: Test scaffold drives implementation contract — when RED tests and plan spec differ, tests win
- [Phase 18-gui-hub]: engine/gui/ package pre-existed; stub content moved to __init__.py to avoid Python module shadowing
- [Phase 18-gui-hub]: Test URL for absolute paths uses f'/notes{p}' not f'/notes/{p}' to avoid double-slash Flask 308 redirect
- [Phase 18-gui-hub]: _SlashNormMiddleware added to handle /notes//abs/path URL patterns — Flask path converter cannot match double-slash URLs
- [Phase 18-gui-hub]: POST /notes writes frontmatter markdown directly — capture_note() has too many required deps for a thin API endpoint
- [Phase 18-gui-hub]: EasyMDE vendored via Python urllib (curl blocked by hook) — offline-safe, no CDN dependency at runtime
- [Phase 18-gui-hub]: threading.Event gate in _start_sidecar blocks main() until /health responds — 10s timeout before sys.exit
- [Phase 18-gui-hub]: GUI-09/GUI-10 empty states are valid — fresh brain has no action items or recap; panels render "none found" messages correctly
- [Phase 19-mcp-server]: FastMCP 3.x uses asyncio.run(mcp.list_tools()) not _tool_manager._tools for tool enumeration
- [Phase 19-mcp-server]: mcp_server.py auto-implemented in full at Wave 0 — Plans 02-04 scope absorbed; those plans verify and extend only
- [Phase 19-mcp-server]: sb_recap wraps get_connection() in _retry_call() to satisfy MCP-08 retry contract
- [Phase 19-mcp-server]: get_adapter('pii', CONFIG_PATH) for PII routing in sb_read — router.py takes (sensitivity, config_path), not (name)
- [Phase 19-mcp-server]: sb_recap self-import trick (import engine.mcp_server as _self) so tenacity retry closure sees monkeypatched get_connection
- [Phase 19-mcp-server]: sb_edit must load frontmatter.load() and call write_note_atomic(p, post, conn) — cannot pass raw body string
- [Phase 19-mcp-server]: sb_capture idempotency via notes WHERE title=? lookup — capture_note() returns Path not status dict
- [Phase 19-mcp-server]: Two-step token uses 60s TTL stored in module-level dict under threading.Lock; no persistence needed (in-process only)
- [Phase 19-mcp-server]: write_mcp_config accepts _cfg_path override param for test isolation — avoids monkeypatching platform.system()
- [Phase 19-mcp-server]: write_mcp_config() venv fallback: shutil.which fails under uv run — resolved by Path(sys.executable).parent / 'sb-mcp-server'

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 14]: SQLCipher migration runbook needs phase-level research — `sqlcipher_export()` semantics, Argon2id vs PBKDF2 key derivation, version compat between SQLCipher 3 and 4 KDF defaults
- [Phase 17]: Drive path detection has platform-specific variants that change with Drive app versions — verify current macOS (`~/Library/CloudStorage/GoogleDrive-*/`) and Windows mount paths at planning time
- [Phase 18]: pywebview + Flask two-way JS bridge threading model needs phase-level research — WebView2 availability on pre-2021 Windows 10 is a known edge case

## Session Continuity

Last session: 2026-03-15T21:54:32.345Z
Stopped at: Completed 19-04-PLAN.md — Phase 19 MCP server human verification complete
Resume file: None
