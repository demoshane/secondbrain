---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Intelligence + GUI Hub
status: executing
stopped_at: Phase 16 context gathered
last_updated: "2026-03-15T19:00:52.006Z"
last_activity: 2026-03-15 — 14-01 complete (deps + RED scaffold); 14-02 task 1 committed (DDL + config)
progress:
  total_phases: 6
  completed_phases: 2
  total_plans: 8
  completed_plans: 8
  percent: 10
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-15)

**Core value:** Zero-friction capture that surfaces the right context at the right moment
**Current focus:** Phase 14 — Embedding Infrastructure

## Current Position

Phase: 14 of 19 (Embedding Infrastructure)
Plan: 14-02 (in progress)
Status: Executing Wave 1
Last activity: 2026-03-15 — 14-01 complete (deps + RED scaffold); 14-02 task 1 committed (DDL + config)

Progress: [█░░░░░░░░░] 10%

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

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 14]: SQLCipher migration runbook needs phase-level research — `sqlcipher_export()` semantics, Argon2id vs PBKDF2 key derivation, version compat between SQLCipher 3 and 4 KDF defaults
- [Phase 17]: Drive path detection has platform-specific variants that change with Drive app versions — verify current macOS (`~/Library/CloudStorage/GoogleDrive-*/`) and Windows mount paths at planning time
- [Phase 18]: pywebview + Flask two-way JS bridge threading model needs phase-level research — WebView2 availability on pre-2021 Windows 10 is a known edge case

## Session Continuity

Last session: 2026-03-15T19:00:51.995Z
Stopped at: Phase 16 context gathered
Resume file: .planning/phases/16-semantic-search-and-digest/16-CONTEXT.md
