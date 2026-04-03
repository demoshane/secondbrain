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

## Milestone: v2.0 — Intelligence + GUI Hub

**Shipped:** 2026-03-16
**Phases:** 6 (14–19) | **Plans:** 23

### What Was Built

- **Local vector embeddings**: sqlite-vec KNN table + sentence-transformers (`all-MiniLM-L6-v2`), content-hash staleness detection, GDPR cascade delete from `note_embeddings`
- **Intelligence layer**: Session recap (`sb-recap`), action item extraction + `sb-actions` CLI, stale nudges (90-day threshold), connection surfacing (cosine > 0.8), proactive budget gate (one notification per session)
- **Semantic search + digest**: `sb-search --semantic`, RRF hybrid ranking, cross-context synthesis (`sb-recap <name>`), weekly digest auto-written to `.meta/digests/` via launchd
- **Setup automation**: Flask HTTP sidecar (`engine/api.py`) on `127.0.0.1:37491`, Drive auto-detection, Ollama auto-install with size warning in `sb-init`
- **Desktop GUI**: `sb-gui` via pywebview — three-panel sidebar/viewer/intelligence layout, EasyMDE editor vendored offline, new note modal, 300ms debounce search
- **MCP server**: `sb-mcp-server` FastMCP stdio with 10 tools, two-step token confirmation for destructive ops, Claude Desktop config auto-written by `sb-init`

### What Worked

- **Incremental architecture** (CLI → API → GUI → MCP): Each phase built on a stable previous layer. Phase 18 (GUI) plugged into Phase 17 (API) with no rework; Phase 19 (MCP) bypassed the GUI entirely and called the engine directly — the layered design paid off.
- **Two-step token pattern for destructive ops**: The `_issue_token` / `_consume_token` pattern for `sb_forget`/`sb_anonymize` via MCP was simple to implement and completely prevents accidental destructive calls from LLM hallucination. Worth reusing in any MCP context with write ops.
- **EasyMDE offline vendoring**: Deciding early to vendor EasyMDE instead of CDN-linking it prevented a class of runtime failures with no internet access. The offline-first constraint forced a better decision.
- **Stub-first TDD continued to hold**: All 6 phases started with Wave 0 RED scaffolds. Phase 19 had 14 tests all passing before human verification.

### What Was Inefficient

- **Traceability table not updated as phases completed**: EMBED-01–04 showed "Pending" at milestone close despite Phase 14 being fully implemented. The traceability table should be updated at phase completion, not just at roadmap creation.
- **Phase 14 embeddings: Intel Mac lazy-import workaround**: sentence-transformers has issues on Intel Mac; a lazy-import workaround was added. This technical debt will need revisiting when moving to M-chip.
- **MCP server human verification was partially blocked**: Live Claude Desktop `sb_search` test couldn't fully complete in CI context — verified via unit tests instead. Functional but not end-to-end verified in the strictest sense.

### Patterns Established

- **Two-step token confirmation**: For any MCP tool that performs irreversible actions, use `_issue_token()` / `_consume_token()` with a 60s TTL. First call returns a token; second call with token executes. Never execute destructive ops on a single call.
- **Flask sidecar as GUI adapter**: `engine/api.py` on a fixed port (`127.0.0.1:37491`) serves as the adapter between native UI frameworks (pywebview) and engine logic. No engine imports in the GUI layer — HTTP only.
- **Offline-first JS vendoring**: Any web assets used in the GUI must be vendored locally. No CDN references at runtime.

### Key Lessons

1. **Update traceability at phase close, not only at roadmap creation.** The EMBED row staleness caused unnecessary ambiguity at milestone close. Each phase execution should end with a traceability row update.
2. **Two-step confirmation is the right default for destructive MCP tools.** Implement it from the start — it is cheap to add and expensive to retrofit after users trust single-call behavior.
3. **The layered architecture (CLI → engine → API → GUI/MCP) scaled cleanly.** Each surface calls the layer below it; no surface imports from another surface. This separation made it trivial to add GUI and MCP without modifying CLI or engine logic.
4. **Intel Mac embedding workaround should be removed on M-chip migration.** The lazy-import workaround in `engine/embeddings.py` exists only for Intel Mac. When migrating to M-chip, run Phase 14 setup fresh to verify native sentence-transformers behavior.

### Cost Observations

- Model: 100% Sonnet (claude-sonnet-4-6)
- Sessions: ~5 sessions, 1 day
- Notable: 6 phases, 23 plans completed in a single day. Semantic search + GUI + MCP in one milestone was ambitious but the layered architecture made each phase independently executable.

---

## Milestone: v4.0 — Memory & Reliability

**Shipped:** 2026-04-03
**Phases:** 22 | **Plans:** 100

### What Was Built
- Architecture hardening: relative paths, FK cascades, junction tables with SQLite auto-sync triggers
- Scale infrastructure: hnswlib ANN index, encrypted backup/restore, chunked embeddings, tiered storage, memory consolidation
- Complete visual redesign: React + Tailwind matching Visily mockups across 8 pages (4 iterative sub-phases)
- Chrome extension: article/selection/Gmail/URL capture + LLM page summarisation
- Smart capture: 5-pass decomposer pipeline replacing monolithic segmenter
- AI provider flexibility: Groq + Ollama + auto-routing with Settings UI
- Comprehensive codebase audit: 31 findings, all remediated across 6 phases

### What Worked
- **Per-phase requirements in ROADMAP.md**: Tracking requirements (ARCH-01, PERF-01, etc.) directly in the roadmap next to phase goals was more practical than a separate centralized REQUIREMENTS.md. Each phase was self-contained.
- **Iterative visual design (41 → 41.1 → 41.2 → 41.3)**: Accepting that a UI redesign needs multiple passes was more efficient than trying to get it perfect in one phase. Each sub-phase had clear scope.
- **Phase 39 codebase audit as quality gate**: A dedicated audit phase before the final stretch caught 31 real issues. The remediation was distributed across subsequent phases rather than creating a single massive fix phase.
- **SQLite triggers for junction tables (48.1)**: Replacing manual dual-write with database triggers eliminated an entire class of consistency bugs permanently.

### What Was Inefficient
- **No centralized v4.0 REQUIREMENTS.md**: While per-phase requirements worked for execution, it made milestone auditing harder — no single place to check coverage.
- **VERIFICATION.md skipped entirely**: The v4.0 workflow didn't create phase VERIFICATION.md files, making the milestone audit rely on inferring completion from summaries. Not a problem in practice but created process debt.
- **4 decimal phases for visual redesign**: Phases 41.1, 41.2, 41.3 were reactive (discovered during execution). Better up-front Visily → implementation gap analysis could have reduced the iteration count.
- **Phase renumbering churn (44→45→46...)**: Inserting phases mid-milestone caused 4 renumbering cascades. Decimal numbering (used for 41.x and 48.1) would have avoided this.

### Patterns Established
- **SQLite triggers over dual-write**: When a JSON column and a junction table must stay in sync, use AFTER INSERT/UPDATE triggers. Never rely on application-level dual-write.
- **Per-phase requirements**: Define requirements with prefixed IDs (ARCH-01, PERF-01) directly in the ROADMAP.md phase section. Self-contained and easy to trace.
- **Codebase audit as milestone quality gate**: Before closing a major milestone, run a structured audit (security, architecture, performance, test coverage) and create remediation phases.

### Key Lessons
1. **Decimal phases are better than renumbering.** Phases 41.1–41.3 and 48.1 caused no disruption. Renumbering 44→48 caused confusion and stale references. Always use decimals for insertions.
2. **Visual redesigns need iterative sub-phases.** A single "redesign everything" phase will always discover gaps on execution. Plan for at least one gap-closure sub-phase from the start.
3. **SQLite triggers > application-level consistency.** The junction table dual-write bug class was eliminated permanently by 4 triggers. This should be the default pattern for any derived data.
4. **Per-phase requirements work for execution but need a milestone-level summary for auditing.** Consider a lightweight rollup step at milestone close.

### Cost Observations
- Model mix: ~70% Sonnet (execution), ~30% Opus (planning, auditing, complex phases)
- Sessions: ~25 sessions over 11 days
- Notable: Phase 39 (codebase audit) was the most cost-effective phase — one Opus session produced 31 actionable findings that shaped 6 subsequent phases

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.5 | ~15 | 13 | First milestone — established stub-first TDD, wave-based execution, Nyquist discipline |
| v2.0 | ~5 | 6 | Layered architecture (CLI→API→GUI→MCP); two-step token confirmation pattern; traceability gap identified |
| v3.0 | ~15 | 20 | React + shadcn/UI rewrite; Playwright e2e; 8-page GUI; smart capture; people graph |
| v4.0 | ~25 | 22 | Per-phase requirements; iterative visual design; codebase audit as quality gate; SQLite triggers |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.5 | ~60+ stubs + implementations | Full path coverage across 14 phases | 0 — all deps explicit in pyproject.toml |
| v2.0 | 14 MCP tests + full intelligence/GUI/search test suites | All 47 requirements covered; 4 EMBED rows stale in traceability | sqlite-vec, sentence-transformers, fastmcp, pywebview, flask, waitress, tenacity |

### Top Lessons (Verified Across Milestones)

1. Stub-first TDD catches integration gaps before they become gap-closure phases.
2. Architecture decisions that change mid-project waste earlier work — lock the runtime before Phase 1.
3. Update traceability rows at phase close — stale rows create ambiguity at milestone completion.
4. Two-step confirmation is the correct default for any destructive operation exposed via MCP.
5. Use decimal phases for insertions — renumbering cascades cause confusion and stale references. (v4.0)
6. SQLite triggers > application-level dual-write for any derived data that must stay in sync. (v4.0)
7. Visual redesigns need iterative sub-phases — plan for at least one gap-closure pass from the start. (v4.0)
