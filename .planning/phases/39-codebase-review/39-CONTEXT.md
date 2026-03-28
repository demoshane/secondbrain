# Phase 39: Full Codebase Review — Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Cross-cutting audit of the entire codebase (39 Python modules, 24 React/TS components, 62 test files). Produces prioritised findings, then executes fixes for Critical/High/Medium severity issues — all within this phase. Low severity findings are documented as tech debt.

This is the first comprehensive review since the project started — 38 phases of accumulated work, never had a cross-cutting audit.

</domain>

<decisions>
## Implementation Decisions

### D-01: Review Tooling
- **No /agent-teams:team-review** — that experimental approach is excluded
- Use parallel `code-reviewer` subagents (one per dimension/area) via the standard Agent tool
- Each reviewer gets a focused scope: backend security, backend architecture, frontend security, test coverage, etc.

### D-02: Phase Structure (Waves)
- **Wave 1 — Audit**: Parallel code-reviewer agents per dimension produce findings docs
- **Wave 2 — Triage**: Consolidate, deduplicate, severity-rank all findings; produce a single prioritised findings doc
- **Wave 3 — Remediation**: Create fix plans for Critical/High/Medium findings, execute them via standard GSD execute flow
- All three waves complete within phase 39 — no handoff to a follow-on phase

### D-03: Execution Model
- Claude executes fixes inline using standard GSD plan → execute flow
- For risky or large fixes (scope unclear, blast radius high, requires destructive change): **surface to user and ask per-finding** before proceeding
- User decides per-finding: fix now, defer, or skip

### D-04: Audit Dimensions — All Four, Equal Weight
- Security
- Architecture
- Performance
- Test coverage
- **Deprecated/dead code** — given the project has gone through multiple refactors across 38 phases, scan for stale code paths, unused functions/endpoints, old patterns that were superseded but not removed
- **Optimisation opportunities** — identify code that could be simplified, consolidated, or made more efficient (e.g. redundant DB queries, N+1 patterns, duplicated logic across modules)

Priority focus within each:
- **Backend (engine/*.py)**: API surface + data handling first — input validation, path traversal, SQL injection, PII exposure via MCP/API; also scan for deprecated function paths left over from refactors (e.g. old capture paths, superseded search logic)
- **Frontend (frontend/src/)**: Security + UX correctness first — XSS, dangerouslySetInnerHTML, unescaped user content, incorrect auth/state handling; also check for unused components or dead routes from the React migration (Phase 27.3)

### D-05: Fix Threshold
- **Critical**: Fix in this phase — data loss or security breach risk
- **High**: Fix in this phase — broken behavior, significant correctness issue
- **Medium**: Fix in this phase — meaningful quality issue, worth addressing while we're here
- **Low**: Document in STATE.md Pending Todos — cosmetic, preference, or minor polish

### D-06: Tech Debt Backlog
- Low severity findings → added to **STATE.md Pending Todos** section
- Consistent with how other deferred items are tracked in this project
- No separate tech-debt file

### Claude's Discretion
- How many parallel code-reviewer agents to spawn per wave (granularity per module group vs per dimension)
- Exact scope boundaries per reviewer (e.g., group engine/ by functional area vs one agent per file batch)
- Finding deduplication and severity calibration approach
- Fix plan grouping (one plan per finding vs group related findings into a single plan)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Security baseline
- `~/.claude/SECURITY.md` — global security rules, data flow, risk matrix, guardrail hooks
- `engine/api.py` — Flask API surface (all public endpoints)
- `engine/mcp_server.py` — MCP tool surface (all sb_* tools)

### Codebase structure
- `engine/` — 39 Python modules (all to be reviewed)
- `frontend/src/components/` — 24 React/TS components
- `tests/` — 62 test files (coverage gap analysis)

### Prior quality work
- Phase 32 CONTEXT.md (`.planning/phases/32-architecture-hardening/32-CONTEXT.md`) — known architectural fixes that were applied
- Phase 35 CONTEXT.md (`.planning/phases/35-brain-consolidation/35-CONTEXT.md`) — consolidation patterns
- `.claude/LEARNINGS.md` in the project — accumulated gotchas from prior phases

No external spec ADRs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `code-reviewer` subagent type — available via Agent tool, specialized for security + best practices review
- `security-auditor` subagent type — available for systematic vulnerability analysis
- `test-automator` subagent type — available for coverage gap identification

### Established Patterns
- Parallel agent spawning via Agent tool — used in prior phases for independent work streams
- GSD plan → execute flow — fix plans in XML format, executed by gsd-executor
- Two-step token pattern for destructive ops (already in mcp_server.py) — check if all destructive MCP tools use it

### Integration Points
- Findings doc → GSD plan files → gsd-executor for remediation
- STATE.md Pending Todos → landing zone for Low severity findings

</code_context>

<specifics>
## Specific Decisions

- `/agent-teams:team-review` is explicitly excluded — do not reference it in plans
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` env flag not needed
- Risky fixes require per-finding user confirmation before execution — do not batch-execute risky changes
- All three waves (audit, triage, remediation) are in scope for phase 39
- Medium severity gets fixed — this is broader than the original stub which only mentioned Critical+High

</specifics>

<deferred>
## Deferred Ideas

- None raised during discussion

</deferred>

---

*Phase: 39-codebase-review*
*Context gathered: 2026-03-27*
