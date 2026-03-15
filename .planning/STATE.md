---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Intelligence + GUI Hub
status: defining_requirements
stopped_at: ""
last_updated: "2026-03-15"
last_activity: "2026-03-15 — Milestone v2.0 started"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Zero-friction capture that surfaces the right context at the right moment
**Current focus:** Phase 1 — Foundation

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-03-15 — Milestone v2.0 started

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
| Phase 02-storage-and-index P03 | 12 | 1 tasks | 4 files |
| Phase 03-ai-layer P00 | 10 | 2 tasks | 6 files |
| Phase 03-ai-layer P01 | 3 | 2 tasks | 7 files |
| Phase 03-ai-layer P02 | 2 | 2 tasks | 3 files |
| Phase 03-ai-layer P04 | 4 | 2 tasks | 4 files |
| Phase 03-ai-layer P03 | 3 | 2 tasks | 3 files |
| Phase 03-ai-layer P05 | 5 | 2 tasks | 0 files |
| Phase 04-automation P03 | 12 | 2 tasks | 6 files |
| Phase 04-automation P02 | 2 | 1 tasks | 2 files |
| Phase 04-automation P00 | 4 | 2 tasks | 10 files |
| Phase 04-automation P01 | 12 | 2 tasks | 3 files |
| Phase 04-automation P04 | 5 | 1 tasks | 2 files |
| Phase 04-automation P05 | 8 | 1 tasks | 3 files |
| Phase 04-automation P07 | 5 | 2 tasks | 2 files |
| Phase 04-automation P08 | 12 | 2 tasks | 8 files |
| Phase 04-automation P11 | 2 | 1 tasks | 2 files |
| Phase 04.1-native-macos-ux-global-cli-launchd-watcher-autostart-git-hook-installer P00 | 2 | 2 tasks | 2 files |
| Phase 04.1-native-macos-ux-global-cli-launchd-watcher-autostart-git-hook-installer P01 | 3 | 3 tasks | 1 files |
| Phase 04.1-native-macos-ux-global-cli-launchd-watcher-autostart-git-hook-installer P02 | 10 | 2 tasks | 1 files |
| Phase 05-gdpr-and-maintenance P00 | 2 | 2 tasks | 5 files |
| Phase 05-gdpr-and-maintenance P01 | 6 | 1 tasks | 3 files |
| Phase 05-gdpr-and-maintenance P02 | 3 | 2 tasks | 2 files |
| Phase 05-gdpr-and-maintenance P03 | 5 | 2 tasks | 0 files |
| Phase 06-integration-gap-closure P02 | 15 | 1 tasks | 2 files |
| Phase 06-integration-gap-closure P01 | 12 | 2 tasks | 4 files |
| Phase 06-integration-gap-closure P00 | 8 | 2 tasks | 4 files |
| Phase 06-integration-gap-closure P03 | 15 | 2 tasks | 2 files |
| Phase 07-fix-path-format-split P00 | 2 | 2 tasks | 3 files |
| Phase 07-fix-path-format-split P01 | 5 | 2 tasks | 1 files |
| Phase 08-fix-update-memory-routing P00 | 3 | 1 tasks | 1 files |
| Phase 08-fix-update-memory-routing P01 | 5 | 2 tasks | 1 files |
| Phase 09-nyquist-sign-off P00 | 5 | 3 tasks | 10 files |
| Phase 10-quick-code-fixes P00 | 5 | 3 tasks | 2 files |
| Phase 11-gdpr-scope-expansion P00 | 2 | 2 tasks | 7 files |
| Phase 11-gdpr-scope-expansion P03 | 15 | 2 tasks | 2 files |
| Phase 12-micro-code-fixes P00 | 15 | 2 tasks | 4 files |
| Phase 12-micro-code-fixes P02 | 5 | 1 tasks | 2 files |
| Phase 12-micro-code-fixes P01 | 2 | 2 tasks | 2 files |
| Phase 12-micro-code-fixes P03 | 5 | 1 tasks | 1 files |
| Phase 12-micro-code-fixes P04 | 15 | 2 tasks | 0 files |
| Phase 13-nyquist-completion P00 | 5 | 2 tasks | 2 files |
| Phase 13-nyquist-completion P01 | 10 | 4 tasks | 3 files |

## Accumulated Context

### Roadmap Evolution

- Phase 4.1 inserted after Phase 4: Native macOS UX — global CLI, launchd watcher autostart, git hook installer (URGENT — day-to-day friction fix)

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
- [Phase 02-storage-and-index]: detect-secrets test uses shutil.which guard to skip outside DevContainer — binary only installed inside container
- [Phase 03-ai-layer]: mock_subprocess_claude is a context manager factory (returns patch()) so tests can use 'with mock_subprocess_claude as mock_run'
- [Phase 03-ai-layer]: pyyaml not added as dependency — test_subagent_frontmatter_valid uses manual key extraction via splitlines()
- [Phase 03-ai-layer]: ClaudeAdapter uses subprocess.run(['claude', '-p', ...]) — no anthropic SDK import (Max plan constraint)
- [Phase 03-ai-layer]: classify() frontmatter field wins over keyword scan — explicit user declaration takes priority
- [Phase 03-ai-layer]: OllamaAdapter default host is host.docker.internal:11434 for DevContainer compatibility
- [Phase 03-ai-layer]: load_config() has no module-level caching — every call reads disk for hot config reload without restart (AI-05)
- [Phase 03-ai-layer]: Unknown sensitivity in get_adapter() falls back to public_model routing (safe default)
- [Phase 03-ai-layer]: init_brain.py writes config.toml as raw string — no tomllib import in init path; idempotent (no overwrite)
- [Phase 03-ai-layer]: RateLimiter uses deque of monotonic timestamps (not a counter) — supports sliding window not fixed window
- [Phase 03-ai-layer]: Subagent .md files committed to repo so install_subagent.py can copy from source-controlled path
- [Phase 03-ai-layer]: CAP-06 memory update path confirmed in ClaudeAdapter (03-03) — no additional file needed in 03-04
- [Phase 03-ai-layer]: Import engine.router as module ref (not from-import) so engine.router.get_adapter patches intercept correctly in tests
- [Phase 03-ai-layer]: CONFIG_PATH alias added to engine/paths.py pointing to same path as CONFIG_FILE
- [Phase 03-ai-layer]: Phase 3 AI layer validated via human approval — no code changes required at gate
- [Phase 03-ai-layer]: PII routing confirmed: test_pii_zero_anthropic_calls passes (OllamaAdapter returned, ClaudeAdapter not invoked)
- [Phase 04-automation]: TYPE_TO_DIR dict used for type->subdir mapping — allows future additions without touching path construction logic
- [Phase 04-automation]: People notes slug omits date prefix — person profiles addressed by name, not creation date
- [Phase 04-automation]: projects and personal types added symmetrically to both QUESTION_SYSTEM_PROMPTS and FALLBACK_QUESTIONS in ai.py
- [Phase 04-automation]: retrieve_context reads note bodies from disk (Path.read_text) not DB body column — file is source of truth, DB is index only
- [Phase 04-automation]: augment_prompt returns query unchanged when no context found — no empty context block injected (cleaner caller contract)
- [Phase 04-automation]: FTS5 test queries must use real tokenizable words — single-char repeated strings don't tokenize as FTS5 words
- [Phase 04-automation]: engine/links.py and engine/rag.py implemented fully in prior session — test files upgraded from xfail stubs to real passing tests
- [Phase 04-automation]: add_backlinks() is best-effort: DB insert failure caught silently so capture is never blocked
- [Phase 04-automation]: Deferred import (from engine.links import add_backlinks inside function body) avoids circular import between capture and links modules
- [Phase 04-automation]: watchdog Observer not started in unit tests — handler class methods tested directly (avoids real filesystem events in CI)
- [Phase 04-automation]: FSEvents history guard uses monotonic-to-wall-clock conversion with 1s slack for ctime comparison
- [Phase 04-automation]: patch engine.router.get_adapter (module ref) not engine.hooks.post_commit.get_adapter — deferred import means get_adapter is not a module-level attribute of post_commit
- [Phase 04-automation]: ensure_person_profile() creates skeleton on first access — eliminates silent skip for missing people profiles
- [Phase 04-automation]: seed_templates() source path relative to __file__ (engine/) so repo templates found regardless of brain_root location; existing files never overwritten matching config.toml seeding contract
- [Phase 04-automation]: BRAIN_SUBDIRS count assertion in test_paths.py updated from 9 to 10 — test must track intentional additions to the list
- [Phase 04-automation]: ask_followup_questions() conn=None param is optional for backwards compat; augment_prompt called only when conn provided
- [Phase 04-automation]: FilesDropHandler redesigned with single shared _batch_timer — all files dropped within DEBOUNCE_SECONDS processed as one batch; rate-limited batches retry after window
- [Phase 04-automation]: Post-commit hook cds to brain repo before uv run; original project dir passed via SB_PROJECT_DIR so git commands target correct repo
- [Phase 04-automation]: on_new_file derives title from path.stem with hyphen/underscore->space and title-case; sensitivity hardcoded to private for dropped files
- [Phase 04-automation]: conn and adapter initialized once before on_new_file closure; conn.close() deferred to after observer.join()
- [Phase 04.1-native-macos-ux]: patch.object(install_native, PLIST_PATH) for hermetic plist write tests without touching ~/Library/LaunchAgents
- [Phase 04.1-native-macos-ux]: write_plist accepts optional plist_path override so tests can redirect output to tmp_path without touching ~/Library/LaunchAgents
- [Phase 04.1-native-macos-ux]: launchctl bootout form is gui/<uid>/<label>; bootstrap form is gui/<uid> <plist_path> — different launchd API shapes
- [Phase 04.1-native-macos-ux]: sb-watch shim path resolved as find_uv().parent / 'sb-watch' — same bin directory as uv binary
- [Phase 04.1-native-macos-ux]: launchd first-run requires manual bootstrap gui/<uid> <plist> — idempotent on subsequent runs; expected macOS behavior
- [Phase 04.1-native-macos-ux]: sb-install entry point module path is install_native:main (not scripts.install_native:main) — hatchling packages scripts/ as flat namespace
- [Phase 05-gdpr-and-maintenance]: Deferred imports inside xfail test bodies ensure --collect-only works before engine.forget and engine.read are implemented
- [Phase 05-gdpr-and-maintenance]: sb-forget and sb-read wired in pyproject.toml at Wave 0 so Wave 1 implementation plans need no toml edits
- [Phase 05-gdpr-and-maintenance]: Exact-path IN (...) for DB deletion in forget_person — avoids LIKE '%slug%' broad-match Pitfall 5
- [Phase 05-gdpr-and-maintenance]: SpyConnection subclass replaces monkey-patch for sqlite3 execute spy — Python 3.14 made conn.execute read-only
- [Phase 05-gdpr-and-maintenance]: _fts5_query() phrase-quoting in search_notes — prevents OperationalError when slug contains hyphens (FTS5 subtraction operator)
- [Phase 05-gdpr-and-maintenance]: SB_PII_PASSPHRASE_INPUT env var used for non-interactive test injection in read_note — consistent with forget_person pattern
- [Phase 05-gdpr-and-maintenance]: Audit log in read_note is best-effort: exception in INSERT never blocks the read (consistent with search.py pattern)
- [Phase 05-gdpr-and-maintenance]: Empty SB_PII_PASSPHRASE triggers immediate denial before getpass prompt — no interactive prompt when no passphrase configured
- [Phase 05-gdpr-and-maintenance]: UAT pre-confirmed by user (9/9 manual steps passed) before this plan ran; checkpoint treated as auto-approved
- [Phase 06-integration-gap-closure]: Deferred import pattern for update_memory() — consistent with add_backlinks; ImportError caught automatically
- [Phase 06-integration-gap-closure]: Patch deferred imports at source module (engine.db.get_connection), not call site (engine.capture.get_connection) — Python 3.14 mock is strict
- [Phase 06-integration-gap-closure]: Store str(md_path) absolute path in reindex — not relative_to(brain_root) — so RAG reads locate files without brain_root reconstruction
- [Phase 06-integration-gap-closure]: classify() called inside on_new_file() per-file with deferred import — mirrors capture.py pattern; removes daemon-level adapter binding
- [Phase 06-integration-gap-closure]: Wave 0 xfail stubs replaced by plain passing tests — all 6 behaviors already implemented in prior plans (06-01, 06-02, 06-03) before wave 0 ran
- [Phase 06-integration-gap-closure]: CAP-09 target (~/.claude/CLAUDE.md) lives outside repo — checkpoint used for manual verification; idempotency guard skips append if section present
- [Phase 07-fix-path-format-split]: Tests use tmp_path.resolve() as brain_root — canonical macOS path contract; raw tmp_path may return /var/... while resolve() gives /private/var/...
- [Phase 07-fix-path-format-split]: Use .resolve() not .absolute() — macOS tmp_path is /var/... symlink to /private/var/...; only .resolve() gives canonical form
- [Phase 07-fix-path-format-split]: No changes to rag.py/forget.py — root cause was exclusively capture's path storage; consumers were already correct
- [Phase 08-fix-update-memory-routing]: Patch engine.router.get_adapter (module ref) in update_memory() tests — consistent with Phase 3/4 pattern
- [Phase 08-fix-update-memory-routing]: update_memory() hardcodes sensitivity='public' internally — call site in capture.py already guards PII before calling this function
- [Phase 08-fix-update-memory-routing]: ClaudeAdapter import removed from engine/ai.py — all adapter calls now go through _router.get_adapter module ref
- [Phase 09-nyquist-sign-off]: Phases with human_needed rows (01, 03, 04, 04.1) carry live-env caveat in Approval — manual-only annotation not blocking nyquist sign-off
- [Phase 10-quick-code-fixes]: update_memory() docstring updated to reflect ModelRouter routing, not ClaudeAdapter
- [Phase 10-quick-code-fixes]: brain_root.resolve() inserted at forget_person() entry — all downstream path ops and DB DELETE paths canonical
- [Phase 11-gdpr-scope-expansion]: Deferred import inside xfail test bodies ensures --collect-only works before modules implemented (consistent with Phase 5 pattern)
- [Phase 11-gdpr-scope-expansion]: prompt_consent() is a NotImplementedError stub in Wave 0 — wiring to main() deferred to plan 11-03
- [Phase 11-gdpr-scope-expansion]: sb-export entry point wired at Wave 0 so plans 11-01/02/03 need no pyproject.toml edits
- [Phase 11-gdpr-scope-expansion]: Consent check placed BEFORE validate_drive_mount in init_brain.py main() — consent gates everything including Drive mount check
- [Phase 11-gdpr-scope-expansion]: Sentinel at brain_root/.meta/consent.json (Drive-synced path) — survives DevContainer rebuilds; devcontainer.json callers must use --yes flag
- [Phase 11-gdpr-scope-expansion]: No passphrase gate on export — Article 20 does not permit withholding personal data; user owns their data
- [Phase 11-gdpr-scope-expansion]: note_path=NULL in audit_log for export — operation-level event, consistent with forget.py and search.py
- [Phase 11-gdpr-scope-expansion]: re.escape(token) always applied before re.sub — tokens may contain email dots, hyphens, parens which are regex metacharacters
- [Phase 11-gdpr-scope-expansion]: FTS5 updated automatically by notes_au trigger on UPDATE notes — no manual rebuild needed for single-note anonymize
- [Phase 12-micro-code-fixes]: test_reindex_stores_absolute_paths was already present — not duplicated; only test_reindex_preserves_people_column added in plan 12-00
- [Phase 12-micro-code-fixes]: Wave 0 test_export_initialises_schema_on_fresh_db passes by design — confirms OperationalError exists (bug present), fix goes in main() not export_brain()
- [Phase 12-micro-code-fixes]: init_schema called in main() not export_brain() — library function receives a ready conn; callers own schema lifecycle
- [Phase 12-micro-code-fixes]: sb-anonymize entry point wired to engine.anonymize:main (already existed — no new code needed)
- [Phase 12-micro-code-fixes]: config_path in ai.py main() defaults to BRAIN_ROOT/.meta/config.toml matching engine/ pattern; lazy import avoids circular import risk
- [Phase 12-micro-code-fixes]: md_path.resolve() not .absolute() in reindex — dereferences macOS symlink; consistent with forget.py and capture.py
- [Phase 12-micro-code-fixes]: people normalisation mirrors tags pattern in reindex.py — isinstance guard + json.dumps; no new imports needed
- [Phase 12-micro-code-fixes]: uv tool install --editable . must be re-run after adding new [project.scripts] entries — tests verify importability but not shell executable registration
- [Phase 13-nyquist-completion]: Phase 10 row 10-00-01 marked manual-only — docstring review has no automated test
- [Phase 13-nyquist-completion]: Phase 11 row 11-03-05 marked manual-only — TTY consent prompt inherently untestable without real terminal; does not block nyquist sign-off
- [Phase 13-nyquist-completion]: Phase 12 VALIDATION.md sign-off missed by 13-00; closed in 13-01 continuation
- [Phase 13-nyquist-completion]: Phase 13 VALIDATION.md and VERIFICATION.md created post-execution to satisfy audit

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1]: Windows `${localEnv:HOME}` expansion with Docker Desktop + WSL2 is untested — must be explicitly verified in Phase 1 before proceeding
- [Phase 1]: `remoteUser` must be set to `vscode` consistently — mixing root/vscode causes Drive sync permission failures
- [Phase 3]: Verify Anthropic SDK version and Ollama model sizes at phase planning time (training data may be stale)
- [Phase 3]: Confirm Ollama is accessible at `host.docker.internal:11434` from inside DevContainer before building adapter

## Session Continuity

Last session: 2026-03-15T13:55:00.737Z
Stopped at: Completed 13-01-PLAN.md — all phases nyquist_compliant: true, v1.5 milestone Nyquist gap fully closed
Resume file: None
