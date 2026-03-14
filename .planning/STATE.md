---
gsd_state_version: 1.0
milestone: v1.5
milestone_name: milestone
status: planning
stopped_at: Completed 02-storage-and-index/02-02-PLAN.md
last_updated: "2026-03-14T15:38:07.074Z"
last_activity: 2026-03-14 — Roadmap created; all 48 v1 requirements mapped across 5 phases
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 14
  completed_plans: 13
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Zero-friction capture that surfaces the right context at the right moment
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: 1 of 5 (Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-14 — Roadmap created; all 48 v1 requirements mapped across 5 phases

Progress: [░░░░░░░░░░] 0%

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
| Phase 01-foundation P00 | 10 | 2 tasks | 11 files |
| Phase 01-foundation P01 | 2 | 2 tasks | 6 files |
| Phase 01-foundation P02 | 2 | 2 tasks | 3 files |
| Phase 01-foundation P03 | 8 | 2 tasks | 6 files |
| Phase 01-foundation P04 | 3 | 1 tasks | 2 files |
| Phase 01-foundation P05 | 1 | 2 tasks | 4 files |
| Phase 01-foundation P07 | 5 | 1 tasks | 2 files |
| Phase 01-foundation P08 | 1 | 2 tasks | 2 files |
| Phase 01-foundation P09 | 3 | 2 tasks | 3 files |
| Phase 02-storage-and-index P00 | 8 | 4 tasks | 4 files |
| Phase 02-storage-and-index P01 | 3 | 2 tasks | 10 files |
| Phase 02-storage-and-index P02 | 2 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-phase]: SQLite lives in named Docker volume only — never Drive-synced; index is rebuildable via /sb-reindex
- [Pre-phase]: PII classification is local-only (rules + frontmatter) — no cloud API call before classification is confirmed false
- [Pre-phase]: ModelRouter (AI-02 through AI-06) is the GDPR enforcement point — must be built before any feature calls an AI API
- [Pre-phase]: .env.host excluded from git AND Drive sync; secrets never in logs or error messages
- [Phase 01-foundation]: Run tests via uv run --no-project --with pytest — engine/ package does not exist yet so hatchling build is skipped
- [Phase 01-foundation]: pyproject.toml dependencies field is inline array inside [project], not a separate [project.dependencies] table (PEP 517)
- [Phase 01-foundation]: remoteUser=vscode (UID 1000) — not root — prevents Drive sync permission failures on bind mounts
- [Phase 01-foundation]: .env.host sourced from ~/.config/second-brain/ (outside ~/SecondBrain Drive folder) — never Drive-synced, never in git
- [Phase 01-foundation]: SQLite uses named Docker volume brain-index-data (not bind mount) — index is rebuildable, never synced to Drive
- [Phase 01-foundation]: .secrets.baseline manually generated outside DevContainer; must be regenerated inside via detect-secrets scan after first open
- [Phase 01-foundation]: pre-commit install deferred to DevContainer postCreateCommand; test_blocks_api_key skips outside container via skipif guard
- [Phase 01-foundation]: Use conn.executescript() for multi-statement SQL in init_schema — trigger bodies contain semicolons that break naive split
- [Phase 01-foundation]: validate_drive_mount writes a .sb-write-probe file before any mkdir — ensures actual write permission on Drive mount
- [Phase 01-foundation]: reindex_brain accepts optional conn parameter so tests can pass in-memory SQLite connection without touching disk
- [Phase 01-foundation]: Relative path from brain_root used as canonical note ID in reindex — portable across installs and containers
- [Phase 01-foundation]: bootstrap.py runs on HOST using Path.home() directly — no engine.paths import (container paths not valid on host)
- [Phase 01-foundation]: FOUND-12 pathlib-only enforced by static analysis tests in test_paths.py — makes convention a hard test failure
- [Phase 01-foundation]: test_blocks_api_key uses AWS AKIA pattern (AKIAIOSFODNN7EXAMPLE) — detect-secrets AWSKeyDetector reliably catches it; pragma: allowlist secret marks fixture as known false positive # pragma: allowlist secret
- [Phase 01-foundation]: detect-secrets has no Anthropic API key plugin as of v1.5.0 — sk-ant-api03-* limitation documented in test_anthropic_key_not_detected
- [Phase 01-foundation]: Venv guard placed at start of main() (after arg parsing, before checks) so warning is visible even if user forgets --dev
- [Phase 01-foundation]: Versioned hook in .githooks/ with core.hooksPath — eliminates host/container hook overwrite race condition
- [Phase 02-storage-and-index]: Defer engine.capture/engine.search imports to test body so pytest --collect-only succeeds before modules exist
- [Phase 02-storage-and-index]: seeded_db and initialized_db guard against missing 'people' column via PRAGMA table_info check
- [Phase 02-storage-and-index]: Temp file always in target.parent via mkstemp(dir=target.parent) — never /tmp — guarantees atomic os.replace on same filesystem
- [Phase 02-storage-and-index]: conn.commit() before os.replace() — DB is source of truth; partial file never exists without a DB record
- [Phase 02-storage-and-index]: Error messages use type(e).__name__ only — body/metadata never interpolated (GDPR-05)
- [Phase 02-storage-and-index]: load_template accepts optional templates_dir override for hermetic testing without touching container paths
- [Phase 02-storage-and-index]: BM25 scores are negative — ORDER BY bm25(notes_fts) ASC gives best-match first; note_path=None for search audit rows (GDPR-05 alignment)

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Windows `${localEnv:HOME}` expansion with Docker Desktop + WSL2 is untested — must be explicitly verified in Phase 1 before proceeding
- [Phase 1]: `remoteUser` must be set to `vscode` consistently — mixing root/vscode causes Drive sync permission failures
- [Phase 3]: Verify Anthropic SDK version and Ollama model sizes at phase planning time (training data may be stale)
- [Phase 3]: Confirm Ollama is accessible at `host.docker.internal:11434` from inside DevContainer before building adapter

## Session Continuity

Last session: 2026-03-14T15:38:07.064Z
Stopped at: Completed 02-storage-and-index/02-02-PLAN.md
Resume file: None
