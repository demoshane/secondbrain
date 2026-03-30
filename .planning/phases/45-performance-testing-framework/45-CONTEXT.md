# Phase 45: Performance Testing Framework — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a performance testing framework that tracks how system performance evolves as the brain grows. Deliverables:

1. `sb-perf` CLI command — runs timed benchmarks against all MCP tools, ask_brain (POST /ask), and recap. Outputs terminal table with delta vs prior run. Soft limit breaches flagged as warnings.
2. Result storage — one JSON result per calendar day (most recent wins), retained 30 days. Last run always available. Stored at `~/SecondBrain/.meta/perf_results/`.
3. GUI Performance page — new tab in TabBar. Summary table (latest vs previous, delta, limit, status) + per-tool history charts.

**In scope:**
- `engine/perf.py` — benchmark runner, result storage, delta computation, soft limits
- `sb-perf` CLI entry point in `pyproject.toml`
- `engine/test_utils.py` — unified test data cleanup utility (used by perf AND extensible for pytest)
- New Flask endpoints: `GET /perf/results` (list), `GET /perf/results/latest` (latest + previous for delta)
- `frontend/src/components/PerformancePage.tsx` — new tab with table + history charts
- TabBar updated to include Performance tab

**Out of scope:**
- Automated scheduling of `sb-perf` (launchd job) — future phase
- Alerting / notifications on breach — future phase
- Coverage of Phase 46+ tools — extend incrementally

</domain>

<decisions>
## Implementation Decisions

### Soft Limits

- **D-01:** Soft limits hardcoded as defaults in `engine/perf.py` — no config required to get started. User can override via `config.toml [perf]` section in a future phase.
- **D-02:** Default limits:
  - Read-only MCP tools (`sb_search`, `sb_read`, `sb_files`, `sb_connections`, `sb_actions`, `sb_list_persons`, `sb_person_context`, `sb_tag`, `sb_tools`): **2s**
  - Write-path MCP tools (`sb_capture`, `sb_edit`, `sb_forget`, `sb_anonymize`, `sb_link`, `sb_unlink`, `sb_remind`): **5s**
  - `ask_brain` (POST /ask, Groq path): **5s**
  - `sb_recap` / `generate_recap_on_demand`: **20s**
  - `sb_digest`: **30s**
- **D-03:** Soft limit breach = warning printed in terminal output, `⚠` in results table. Does NOT cause non-zero exit — performance testing is observational.

### CLI Invocation

- **D-04:** `sb-perf` — runs full suite by default.
- **D-05:** `sb-perf --tool <tool_name>` — runs a single tool benchmark. Useful for spot-checks after targeted changes.
- **D-06:** `sb-perf --json` — outputs machine-readable JSON instead of terminal table.
- **D-07:** `sb-perf --cleanup` — purges orphaned `__perf_test__` notes from the brain. Also runs automatically at the START of every perf run (pre-flight cleanup before creating new fixtures).
- **D-08:** Exit code always 0 — breaches are warnings, not failures.

### Synthetic Fixture Strategy

- **D-09:** All test-generated notes use `__perf_test__` title prefix. Cleanup: `DELETE WHERE title LIKE '__perf_test__%'`.
- **D-10:** 1 fixture note per write-path tool test. Exception: `sb_capture_batch` tests with a batch of 3.
- **D-11:** Cleanup utility lives in `engine/test_utils.py` with a generic `cleanup_test_notes(prefix: str)` function. `sb-perf` calls it with `"__perf_test__"`. Pytest fixtures can call it with their own prefix (e.g. `"__pytest__"`). This unified pattern prevents test data accumulation across all test types.
- **D-12:** If `--cleanup` runs and finds orphans, it reports how many were deleted before proceeding.

### Result Storage

- **D-13:** One JSON file per calendar day: `~/SecondBrain/.meta/perf_results/YYYY-MM-DD.json`. If run twice in a day, the file is overwritten (most recent wins).
- **D-14:** Files older than 30 days are deleted at the start of each run (rotation). Exception: the most recent file is always retained regardless of age.
- **D-15:** JSON schema per result file:
  ```json
  {
    "run_at": "<ISO timestamp>",
    "tool_results": [
      {
        "tool": "<tool_name>",
        "elapsed_ms": 1234,
        "limit_ms": 5000,
        "status": "pass" | "warn" | "error",
        "error": null | "<message>"
      }
    ]
  }
  ```

### GUI Performance Page

- **D-16:** New tab in `TabBar.tsx` — "Performance" with an appropriate icon (e.g., `Gauge` from lucide-react). Sits after the Intelligence tab.
- **D-17:** Page layout: summary table at top (Tool | Latest | Previous | Delta | Limit | Status), per-tool history charts below (30-day trend, one chart per tool or grouped).
- **D-18:** GUI is read-only — no "Run benchmark" button. `sb-perf` writes results to disk; GUI reads from the Flask API.
- **D-19:** Delta display: show as `+Xms` (regression) or `-Xms` (improvement). Color: red for regression beyond limit, green for improvement, grey for within-limit change.

### Flask API

- **D-20:** `GET /perf/results` — returns list of available result dates (last 30 days).
- **D-21:** `GET /perf/results/latest` — returns latest result + previous result (for delta computation in GUI). If only one result exists, `previous` is null.
- **D-22:** `GET /perf/results/<date>` — returns full result for a specific date (for history charts).

### Claude's Discretion

- Choice of charting library for history charts (recharts already in use in the frontend is preferred)
- Exact icon for the Performance tab
- Error handling when a tool throws an exception mid-benchmark (record as `status: "error"`, continue suite)
- Exact table styling — follow existing page conventions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine patterns
- `engine/perf.py` — does not exist yet; create it
- `engine/test_utils.py` — does not exist yet; create it (unified cleanup utility)
- `engine/health.py` — reference for how a standalone CLI tool is structured in this codebase
- `engine/intelligence.py` — ask_brain() implementation; perf runner calls `POST /ask` endpoint, not the function directly

### Flask API patterns
- `engine/api.py` — existing route patterns, error handling, JSON response shape

### Frontend patterns
- `frontend/src/components/IntelligencePage.tsx` — reference for a full page layout
- `frontend/src/components/TabBar.tsx` — where Performance tab must be added
- `frontend/src/App.tsx` — where page routing and tab state is managed

### Project config
- `pyproject.toml` — `[project.scripts]` section; `sb-perf` entry point must be added here

### MCP tool list
- `engine/mcp_server.py` — authoritative list of all MCP tools to benchmark

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `engine/health.py` — standalone CLI module pattern; `sb-perf` should follow the same structure
- `recharts` — already a frontend dependency (used in HealthScoreGauge area); use for history charts
- `lucide-react` — icon library already in use; pick a Gauge or Activity icon for the tab

### Established Patterns
- CLI entry points: `engine/<module>:<function>` registered in `pyproject.toml [project.scripts]`
- Flask routes: all in `engine/api.py`; new `/perf/*` routes follow existing patterns
- GUI pages: one component file per page in `frontend/src/components/`; page selection driven by `currentView` state in `App.tsx`
- Result persistence: `~/SecondBrain/.meta/` is the canonical location for system metadata not synced to Drive

### Integration Points
- `TabBar.tsx` needs a new "Performance" tab entry
- `App.tsx` needs `PerformancePage` import and `currentView === 'performance'` render branch
- `engine/api.py` gets new `/perf/*` routes
- `pyproject.toml` gets `sb-perf = "engine.perf:main"`

</code_context>

<specifics>
## Specific Ideas

- "We should stop to think if our approach is right or we can optimise" — the warning on breach is intentionally soft; it's a prompt for human review, not an automated gate.
- Cleanup must be fail-safe — if `sb-perf` crashes mid-run, `--cleanup` (or the pre-flight at the next run) must recover the brain state. The `__perf_test__` prefix is the safety net.
- Unified cleanup pattern (`engine/test_utils.py`) should be designed so pytest tests can adopt the same prefix convention going forward — this is a long-term quality-of-life improvement, not just a one-off.

</specifics>

<deferred>
## Deferred Ideas

- Scheduled `sb-perf` runs via launchd — future phase
- Breach alerting / macOS notifications — future phase
- Configurable limits via `config.toml [perf]` — currently hardcoded; config override can be added later
- `--group ai / --group read / --group write` named subsets — `--tool` filter covers the immediate need

</deferred>

---

*Phase: 45-performance-testing-framework*
*Context gathered: 2026-03-30*
