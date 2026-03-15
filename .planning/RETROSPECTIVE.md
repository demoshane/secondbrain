# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.5 — Second Brain MVP

**Shipped:** 2026-03-15
**Phases:** 13 | **Plans:** 60 | **Sessions:** ~15

### What Was Built

- **SQLite FTS5 full-text search engine** with BM25 ranking, type-scoped queries, RAG-lite context injection, and atomic write-then-index capture pipeline
- **10-command CLI** (`sb-capture`, `sb-search`, `sb-read`, `sb-watch`, `sb-export`, `sb-forget`, `sb-anonymize`, `sb-update-memory`, `sb-reindex`, `sb-check-links`) installed globally via `uv tool`
- **Multi-model AI routing**: Claude (via Claude Code/MCP) for public/private content; Ollama for PII — classifier runs locally before any API call, enforced by sensitivity tier architecture
- **GDPR compliance trio**: Article 17 erasure (`sb-forget` with FTS5 rebuild), Article 20 portability (`sb-export`), anonymization (`sb-anonymize`), passphrase PII gate, full audit log, first-run consent prompt
- **Native macOS integration**: launchd LaunchAgent for watcher daemon, `uv tool` global install, git hook installer, 10 Claude Code slash commands in `.claude/commands/`
- **Proactive AI capture**: follow-up questions on every capture, `update_memory()` wiring, `~/.claude/CLAUDE.md` proactive offer instructions, `second-brain` subagent spec

### What Worked

- **Stub-first TDD (Wave 0 → Wave 1)**: Writing all test stubs before implementation prevented scope creep, caught integration gaps early, and made every phase independently verifiable. Tests defined the contract; implementation filled it.
- **Wave-based parallel execution**: Wave 1a/1b/1c plans ran in parallel where there were no dependencies, consistently saving time on multi-component phases (especially Phase 6, 11, 12).
- **Nyquist validation discipline**: Requiring `nyquist_compliant: true` on every phase created a forcing function that caught 5 integration gaps before the milestone shipped. The audit step was worth the extra phase cost.
- **GDPR-first design**: Treating GDPR as a first-class architecture concern (sensitivity tier, local routing enforcement, erasure cascade) from Phase 1 meant no retrofitting. The three-tier `content_sensitivity` field was the correct level of granularity.
- **Sensitivity tier architecture**: `public / private / pii` is simple enough to reason about, maps cleanly to routing rules, and requires no NLP classification — purely from frontmatter set at capture time.

### What Was Inefficient

- **Gap closure required 5 phases (6–12)**: The main v1.5 roadmap (Phases 1–5 + 4.1) shipped incomplete. Five follow-on phases were needed to close integration gaps — path format split, routing bypass, GDPR scope expansion, micro-code fixes, Nyquist completion. Better up-front integration testing in each phase would have caught these during the phase, not after.
- **Nyquist compliance retrofitted twice**: Phase 9 did a batch sign-off across 9 phases, then Phase 13 had to revisit Phases 10–11 immediately after. Nyquist validation should be the final step of each phase, not a separate retrospective pass.
- **Phase 4 Automation ran 12 plans vs. the original 7**: Five gap closure plans were appended after initial completion. The phase's scope was underestimated — file watcher headless mode, templates seeding, and RAG wiring were each non-trivial and deserved dedicated plans from the start.
- **DevContainer architecture abandoned mid-project**: The original design used a Docker DevContainer with named volumes. This was replaced by a native macOS install (`uv tool` + launchd). The DevContainer scaffolding in Phase 1 was partially wasted work.

### Patterns Established

- **Stub-first TDD**: Every phase starts with a Wave 0 plan that writes test stubs for all new behaviors before any implementation. Implementation plans (Wave 1+) must make stubs pass. Never write implementation without a test stub first.
- **Multi-model routing via adapter pattern**: `ModelRouter` selects adapter based on `content_sensitivity`. New models added by implementing `engine/adapters/<model>.py` — no changes to capture or AI logic. Extend, don't modify.
- **Sensitivity tier architecture**: Three tiers (`public / private / pii`) set at capture time in YAML frontmatter. Routing, display gating, and audit behavior all branch on this field. It is the single source of truth for content sensitivity.
- **Wave-based parallel execution**: Multi-component phases are decomposed into Wave 1a / 1b / 1c plans that can execute in parallel. Dependencies are explicit in plan headers. This cuts wall-clock time on large phases.
- **Nyquist as phase exit gate**: A phase is not complete until its `VALIDATION.md` has `nyquist_compliant: true`. This is the last step of every phase, not a separate audit phase.

### Key Lessons

1. **Integration gaps are cheaper to catch in-phase than post-milestone.** The 5 gap-closure phases (6–12) added significant overhead. Each phase should end with an integration smoke test that exercises the full path from CLI entry to DB — not just unit tests.
2. **Architecture decisions that change mid-project (DevContainer → native) waste earlier work.** Lock the runtime environment before Phase 1 starts. If the architecture changes, explicitly retire the old scaffolding rather than leaving it in place.
3. **Nyquist validation must be the final step of every phase.** Running a batch Nyquist pass (Phase 9) and then needing a second one (Phase 13) immediately after shows the pattern wasn't enforced consistently. Enforce it as a phase completion criterion, not a retrospective audit.
4. **GDPR scope expands if not explicitly bounded.** "Right to erasure" in Phase 5 expanded to include export (Article 20), anonymization, and consent in Phase 11 — all valid requirements but unplanned. Define GDPR scope explicitly at the milestone start and lock it.
5. **Absolute paths in DB from the start.** The path format split (Phase 7) — where some DB rows had relative paths and others absolute — broke RAG and forget. All DB rows should store `str(path.resolve())`. Establish this constraint in the schema design phase.

### Cost Observations

- Model: 100% Sonnet (claude-sonnet-4-6) — no Opus, no Haiku
- Sessions: ~15 sessions over 2 days
- Notable: Sonnet was sufficient for all 60 plans including architecture decisions, TDD scaffolding, and GDPR implementation. No session required Opus escalation. The Max plan (no API key) worked seamlessly throughout via Claude Code/MCP.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.5 | ~15 | 13 | First milestone — established stub-first TDD, wave-based execution, Nyquist discipline |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.5 | ~60+ stubs + implementations | Full path coverage across 14 phases | 0 — all deps explicit in pyproject.toml |

### Top Lessons (Verified Across Milestones)

1. Stub-first TDD catches integration gaps before they become gap-closure phases.
2. Architecture decisions that change mid-project waste earlier work — lock the runtime before Phase 1.
