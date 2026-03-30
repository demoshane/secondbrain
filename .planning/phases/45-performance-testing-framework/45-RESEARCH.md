# Phase 45: Performance Testing Framework — Research

**Researched:** 2026-03-30
**Domain:** Python benchmarking CLI, Flask API, React/TypeScript charting
**Confidence:** HIGH

## Summary

Phase 45 builds `sb-perf` — a timed benchmark suite for all MCP tools, ask_brain, and recap. The architecture is clearly defined in CONTEXT.md. All implementation uses existing project patterns: `engine/health.py` as the CLI module template, `engine/api.py` route patterns, `App.tsx`/`TabBar.tsx`/`UIContext.tsx` for frontend tab integration.

The single significant **finding that contradicts CONTEXT.md**: recharts is listed as "already in use in the frontend" but is NOT in `frontend/package.json`. No charting library is currently installed. History charts require adding a dependency. Options: install recharts (~130KB gzip), use a lighter alternative, or build SVG sparklines manually (no dep, consistent with the existing HealthScoreGauge SVG approach).

**Primary recommendation:** Use hand-drawn SVG line charts (no new dependency) for the 30-day trend charts — the HealthScoreGauge already establishes this pattern and the data volume is small (≤30 data points per tool). If full-featured charts are preferred, add recharts as a new dependency.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Soft Limits (D-01 through D-03)**
- Hardcoded defaults in `engine/perf.py`; no config required
- Read-only MCP tools: 2s. Write-path tools: 5s. ask_brain (Groq path): 5s. sb_recap/generate_recap: 20s. sb_digest: 30s
- Breach = terminal warning + ⚠ in table. Does NOT cause non-zero exit.

**CLI (D-04 through D-08)**
- `sb-perf` — full suite by default
- `sb-perf --tool <name>` — single tool benchmark
- `sb-perf --json` — machine-readable JSON output
- `sb-perf --cleanup` — purge orphaned `__perf_test__` notes; also runs automatically at START of every run
- Exit code always 0

**Synthetic Fixtures (D-09 through D-12)**
- All test notes use `__perf_test__` title prefix; cleanup via `DELETE WHERE title LIKE '__perf_test__%'`
- 1 fixture note per write-path tool; exception: sb_capture_batch uses batch of 3
- Cleanup utility in `engine/test_utils.py` with `cleanup_test_notes(prefix: str)` — usable by pytest too
- `--cleanup` reports orphan count before proceeding

**Result Storage (D-13 through D-15)**
- One JSON file per calendar day: `~/SecondBrain/.meta/perf_results/YYYY-MM-DD.json`
- Files older than 30 days deleted at run start (rotation); most recent always retained
- JSON schema defined in CONTEXT.md (run_at, tool_results array with tool/elapsed_ms/limit_ms/status/error)

**GUI (D-16 through D-19)**
- New "Performance" tab in TabBar after Intelligence; Gauge or Activity icon from lucide-react
- Layout: summary table top + per-tool history charts below
- Read-only GUI — no "Run benchmark" button
- Delta: `+Xms` (regression, red if beyond limit) / `-Xms` (improvement, green) / grey for within-limit

**Flask API (D-20 through D-22)**
- `GET /perf/results` — list of available result dates (last 30 days)
- `GET /perf/results/latest` — latest + previous (previous=null if only one exists)
- `GET /perf/results/<date>` — full result for a specific date

### Claude's Discretion

- Choice of charting library for history charts (recharts preferred if in use — but it is NOT currently installed)
- Exact icon for the Performance tab
- Error handling when a tool throws mid-benchmark (record as `status: "error"`, continue suite)
- Exact table styling — follow existing page conventions

### Deferred Ideas (OUT OF SCOPE)

- Scheduled `sb-perf` runs via launchd
- Breach alerting / macOS notifications
- Configurable limits via `config.toml [perf]`
- `--group ai / --group read / --group write` named subsets
</user_constraints>

---

## Standard Stack

### Core (Python side)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `time` / `timeit` | stdlib | Elapsed timing via `time.monotonic()` | No dep; monotonic clock avoids NTP skew |
| `json` | stdlib | Result file serialisation | Already project standard |
| `pathlib.Path` | stdlib | File I/O, `perf_results/` dir management | Already project standard |
| `argparse` | stdlib | CLI flags (`--tool`, `--json`, `--cleanup`) | Pattern from `engine/health.py` |
| `datetime` | stdlib | YYYY-MM-DD filename, ISO timestamps, 30-day rotation | Already project standard |

### Core (Frontend side)
| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| `lucide-react` | 0.577.0 (installed) | Tab icon (Gauge or Activity) | Already in `package.json` |
| `recharts` | NOT INSTALLED | History charts | Must be added if used |

**IMPORTANT:** recharts is referenced in CONTEXT.md as "already in use" but is absent from `frontend/package.json`. The only charting component in the codebase is `health-score-gauge.tsx`, which uses hand-drawn SVG. Two valid paths:

1. **Add recharts** (`npm install recharts`) — full-featured, ~130KB gzip, standard React charting
2. **Hand-drawn SVG sparklines** — zero new dep, consistent with existing HealthScoreGauge pattern, sufficient for 30-point trend lines

**Recommendation (Claude's discretion):** Hand-drawn SVG sparklines. The data is simple (≤30 points, one value per day), the HealthScoreGauge SVG pattern is already established, and avoiding a new dependency keeps the bundle lean. recharts would be overkill.

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | 0.27+ (installed) | HTTP call for `POST /ask` benchmark | Import directly for ask_brain timing |

**Installation (if recharts chosen):**
```bash
cd /Users/tuomasleppanen/second-brain/frontend && npm install recharts
```

---

## Architecture Patterns

### Module Structure

```
engine/
├── perf.py           # NEW: benchmark runner, result storage, delta, soft limits, main()
├── test_utils.py     # NEW: cleanup_test_notes(prefix), reusable by pytest
└── api.py            # MODIFIED: 3 new /perf/* routes appended

frontend/src/
├── components/
│   └── PerformancePage.tsx   # NEW: summary table + history charts
├── contexts/
│   └── UIContext.tsx          # MODIFIED: add 'performance' to View union type
└── App.tsx                    # MODIFIED: import + render branch for PerformancePage

frontend/src/components/
└── TabBar.tsx                 # MODIFIED: add Performance tab entry

pyproject.toml                 # MODIFIED: add sb-perf entry point
```

### Pattern 1: CLI Module Structure (from health.py)

`engine/perf.py` follows the same pattern as `engine/health.py`:

```python
# Source: engine/health.py — established CLI module pattern
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="sb-perf", add_help=True)
    parser.add_argument("--tool", help="Run a single tool benchmark")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--cleanup", action="store_true", help="Purge orphaned test notes")
    args = parser.parse_args()
    # ... dispatch
```

### Pattern 2: Timing a benchmark

Use `time.monotonic()` for sub-second precision with no NTP interference:

```python
import time

def _time_tool(fn, *args, **kwargs) -> tuple[float, str | None]:
    """Returns (elapsed_ms, error_message_or_None)."""
    start = time.monotonic()
    try:
        fn(*args, **kwargs)
        return (time.monotonic() - start) * 1000, None
    except Exception as exc:
        return (time.monotonic() - start) * 1000, str(exc)
```

### Pattern 3: MCP tools — call via direct Python import, not over stdio

`sb-perf` calls MCP tool functions directly (not via MCP protocol), the same way `engine/health.py` calls `engine/brain_health.py` directly. This is faster and avoids the MCP transport overhead. The MCP tool functions in `mcp_server.py` are regular Python functions — they can be imported and called directly.

For `ask_brain` (POST /ask), the runner must call the HTTP endpoint because `ask_brain()` is in `engine/intelligence.py` and requires a live Flask context. Use `httpx` (already in dependencies) to POST `http://127.0.0.1:37491/ask`.

**Important caveat:** If sb-api is not running, ask_brain benchmark must be marked `status: "error"` and the suite must continue. Never let a connection failure abort the whole run.

### Pattern 4: Flask route addition (from api.py)

```python
# Source: engine/api.py — route pattern
@app.get("/perf/results")
def perf_list_results():
    from engine.perf import list_result_dates
    return jsonify({"dates": list_result_dates()})

@app.get("/perf/results/latest")
def perf_latest():
    from engine.perf import get_latest_with_previous
    data = get_latest_with_previous()
    return jsonify(data)

@app.get("/perf/results/<date>")
def perf_by_date(date: str):
    from engine.perf import get_result_by_date
    result = get_result_by_date(date)
    if result is None:
        from flask import abort
        abort(404)
    return jsonify(result)
```

### Pattern 5: UIContext — adding a new tab

Three files must change together:

```typescript
// UIContext.tsx — add 'performance' to the View union
type View = 'notes' | 'actions' | 'people' | 'meetings' | 'projects' | 'intelligence' | 'inbox' | 'links' | 'performance'

// TabBar.tsx — add entry to TABS array (after 'links')
{ id: 'performance' as const, label: 'Performance', icon: Gauge },
// Import: import { ..., Gauge } from 'lucide-react'

// App.tsx — add render branch
} : currentView === 'performance' ? (
  <PerformancePage />
) : null}
// Import: import { PerformancePage } from './components/PerformancePage'
```

### Pattern 6: Result file storage

```python
from pathlib import Path
import datetime, json

PERF_DIR = Path.home() / "SecondBrain" / ".meta" / "perf_results"

def save_result(data: dict) -> Path:
    PERF_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()  # "YYYY-MM-DD"
    path = PERF_DIR / f"{today}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path

def rotate_old_results() -> None:
    """Delete files older than 30 days, always keeping the most recent."""
    files = sorted(PERF_DIR.glob("*.json"))  # lexicographic = chronological for YYYY-MM-DD
    if not files:
        return
    cutoff = datetime.date.today() - datetime.timedelta(days=30)
    for f in files[:-1]:  # never delete the last file
        try:
            file_date = datetime.date.fromisoformat(f.stem)
            if file_date < cutoff:
                f.unlink()
        except (ValueError, OSError):
            pass
```

### Pattern 7: test_utils.py cleanup function

```python
# engine/test_utils.py
from engine.db import get_connection

def cleanup_test_notes(prefix: str = "__perf_test__") -> int:
    """Delete notes whose title starts with prefix. Returns count deleted."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT path FROM notes WHERE title LIKE ?",
            (prefix + "%",)
        ).fetchall()
        count = len(rows)
        conn.execute("DELETE FROM notes WHERE title LIKE ?", (prefix + "%",))
        conn.commit()
    # Also delete physical files
    from engine.paths import BRAIN_ROOT
    for (path,) in rows:
        abs_path = BRAIN_ROOT / path
        try:
            abs_path.unlink(missing_ok=True)
        except OSError:
            pass
    return count
```

Note: must also clean FTS5 index and embeddings. Mirror the pattern from `engine/forget.py` for cascading deletes.

### Pattern 8: SVG sparkline (no recharts dep)

A minimal 30-day trend sparkline using SVG:

```tsx
// Inline SVG sparkline — no external dep, consistent with HealthScoreGauge
function Sparkline({ values, width = 120, height = 32 }: { values: number[], width?: number, height?: number }) {
  if (values.length < 2) return <span className="text-muted-foreground text-xs">—</span>
  const max = Math.max(...values)
  const min = Math.min(...values)
  const range = max - min || 1
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * width
    const y = height - ((v - min) / range) * height
    return `${x},${y}`
  }).join(' ')
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline points={points} fill="none" stroke="hsl(var(--primary))" strokeWidth="1.5" />
    </svg>
  )
}
```

### Anti-Patterns to Avoid

- **Calling MCP tools over stdio for benchmarking:** Adds transport overhead and requires a running MCP server process. Call Python functions directly.
- **Using `time.time()` instead of `time.monotonic()`:** `time.time()` is affected by NTP adjustments; monotonic is the right clock for elapsed measurement.
- **Aborting suite on one tool error:** The suite must mark `status: "error"` and continue. Never raise from the benchmark runner.
- **Running `sb-perf` against the real brain for write-path tests without cleanup:** Must create `__perf_test__` prefixed notes and clean up both before and after.
- **Hardcoding `~/SecondBrain/.meta/perf_results/`:** Use `engine.paths.META_DIR / "perf_results"` so `BRAIN_PATH` env var override works correctly in tests.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Monotonic elapsed time | Custom timer class | `time.monotonic()` | stdlib, correct semantics |
| JSON file I/O | Custom serialiser | `json.dumps` / `Path.write_text` | Already project standard |
| CLI arg parsing | Manual sys.argv | `argparse` (see health.py) | Already established pattern |
| SVG line chart (simple) | recharts installation | Inline SVG polyline | Zero dep, 15 lines |
| DB cleanup | Raw SQL + cascade logic | Mirror `engine/forget.py` cascade | FTS5/embeddings cascade already solved |

---

## Common Pitfalls

### Pitfall 1: recharts assumed installed but isn't
**What goes wrong:** CONTEXT.md says "recharts already in use" — this is inaccurate. Package is not in `frontend/package.json`. Frontend build fails if recharts is imported.
**Why it happens:** Context written before verifying the dependency manifest.
**How to avoid:** Use SVG sparklines (no dep) OR explicitly add `npm install recharts` as a Wave 0 task if recharts is chosen.
**Warning signs:** Build error: `Cannot resolve module 'recharts'`

### Pitfall 2: META_DIR path not using engine.paths
**What goes wrong:** `~/SecondBrain/.meta/perf_results/` hardcoded; tests fail because `BRAIN_PATH` env var is not respected.
**Why it happens:** Forgetting that tests monkeypatch `BRAIN_ROOT` and `META_DIR`.
**How to avoid:** Always import `META_DIR` from `engine.paths`: `PERF_DIR = META_DIR / "perf_results"`. This inherits the env override.

### Pitfall 3: MCP write-path tools create real notes without cleanup
**What goes wrong:** `sb_capture`, `sb_edit`, etc. write to the real brain. If `sb-perf` crashes mid-run, orphan notes accumulate.
**Why it happens:** No pre-flight cleanup on abnormal exit.
**How to avoid:** Pre-flight `cleanup_test_notes("__perf_test__")` at the start of every run (D-07). The `--cleanup` standalone flag also covers manual recovery.

### Pitfall 4: ask_brain benchmark hangs when sb-api is down
**What goes wrong:** `httpx.post(...)` with default timeout hangs indefinitely if sb-api is not running.
**Why it happens:** Missing timeout parameter.
**How to avoid:** Always set `timeout=10.0` (or the soft limit value) on the httpx call. Catch `httpx.ConnectError` and record as `status: "error"`.

### Pitfall 5: View union type not updated in UIContext.tsx
**What goes wrong:** TypeScript compilation error: `'performance'` is not assignable to `View`.
**Why it happens:** Three files must change atomically: UIContext.tsx, TabBar.tsx, App.tsx.
**How to avoid:** Always update UIContext.tsx first (it defines the type), then TabBar.tsx and App.tsx.

### Pitfall 6: FTS5 and embeddings not cleaned up in test_utils.py
**What goes wrong:** `cleanup_test_notes()` deletes from `notes` table but orphan rows remain in `notes_fts` (FTS5 trigger) and `note_embeddings`.
**Why it happens:** FTS5 is managed by triggers; `note_embeddings` may have no ON DELETE CASCADE.
**How to avoid:** Mirror `engine/forget.py` cleanup logic. Check: `DELETE FROM note_embeddings WHERE note_path = ?` and let FTS5 triggers handle their own cleanup (they are ON DELETE CASCADE in SQLite FTS5).

---

## Code Examples

Verified patterns from codebase reading:

### health.py — main() skeleton to mirror
```python
# Source: engine/health.py:278-316
def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="sb-health", add_help=True)
    parser.add_argument("--brain", action="store_true", help="...")
    args = parser.parse_args()
    if args.brain:
        _run_brain_health(); return
    # ... loop over checks, print with STATUS_ICON
    sys.exit(1 if fails else 0)  # perf will always exit(0)
```

### api.py — Flask route pattern
```python
# Source: engine/api.py:159-161
@app.get("/health")
def health():
    return jsonify({"status": "ok", "port": 37491, "warnings": _startup_warnings})
```

### UIContext.tsx — View union
```typescript
// Source: frontend/src/contexts/UIContext.tsx:3
type View = 'notes' | 'actions' | 'people' | 'meetings' | 'projects' | 'intelligence' | 'inbox' | 'links'
// → Must add 'performance'
```

### TabBar.tsx — TABS array
```typescript
// Source: frontend/src/components/TabBar.tsx:5-14
const TABS = [
  { id: 'notes' as const, label: 'Notes', icon: FileText },
  // ...
  { id: 'links' as const, label: 'Links', icon: Link },
  // → Add: { id: 'performance' as const, label: 'Performance', icon: Gauge }
]
```

### App.tsx — render chain
```typescript
// Source: frontend/src/App.tsx:98-104
} : currentView === 'intelligence' ? (
  <IntelligencePage />
) : currentView === 'inbox' ? (
  <InboxPage />
) : currentView === 'links' ? (
  <LinksPage />
) : null}
// → Add 'performance' branch before ': null'
```

### pyproject.toml — entry point pattern
```toml
# Source: pyproject.toml:33-56
sb-health = "engine.health:main"
# → Add: sb-perf = "engine.perf:main"
```

---

## MCP Tools to Benchmark

Full list from `engine/mcp_server.py` (verified by grep for `@mcp.tool()`):

**Read-only (2s limit):** sb_search, sb_read, sb_files, sb_connections, sb_actions, sb_list_persons, sb_person_context, sb_tag (read mode), sb_tools

**Write-path (5s limit):** sb_capture, sb_capture_batch (batch of 3), sb_edit, sb_forget, sb_anonymize, sb_link, sb_unlink, sb_remind

**AI-heavy (tiered limits):** sb_recap (20s), sb_digest (30s), ask_brain via POST /ask (5s)

**Tools to skip / handle specially:**
- `sb_forget` and `sb_anonymize` require a `confirm_token` — the runner must first call to get the token, then call again with it. Since these are write-path tools using synthetic fixtures, this is expected.
- `sb_merge_duplicates`, `sb_merge_confirm`, `sb_find_stubs`, `sb_cleanup_connections`, `sb_health_trend`, `sb_create_person` — not listed in D-02 soft limits; include at write-path 5s default or omit from initial suite per Claude's discretion.
- `sb_rename` — not in CONTEXT.md's limit list; treat as write-path 5s.
- `sb_capture_smart` — write-path 5s (AI inference; may be slow).
- `sb_capture_link` — write-path 5s.
- `sb_actions_done` — write-path 5s (requires creating a test action item first).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | engine/perf.py | ✓ (pinned) | 3.13 | — |
| engine.db / engine.paths | perf.py, test_utils.py | ✓ | — | — |
| httpx | ask_brain benchmark | ✓ | 0.27+ | Mark ask_brain as error if unavailable |
| lucide-react Gauge icon | TabBar.tsx | ✓ (lucide-react 0.577.0) | verify icon exists | Use Activity icon as fallback |
| recharts | History charts (if chosen) | ✗ | not installed | Use SVG sparklines (recommended) |
| sb-api (port 37491) | ask_brain timing | Runtime dep | — | Mark as error, continue suite |
| Ollama (nomic-embed-text) | sb_capture (embeddings) | Runtime dep | — | Embeddings skip is graceful in capture.py |

**Missing dependencies with no fallback:** None that block execution.

**Missing dependencies with fallback:**
- recharts: use SVG sparklines instead (no install needed)
- sb-api not running: ask_brain marks `status: "error"`, suite continues

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_perf.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PERF-01 | `cleanup_test_notes()` deletes DB rows + files | unit | `uv run pytest tests/test_perf.py::test_cleanup_test_notes -x` | ❌ Wave 0 |
| PERF-02 | Result file saved as YYYY-MM-DD.json | unit | `uv run pytest tests/test_perf.py::test_save_result -x` | ❌ Wave 0 |
| PERF-03 | Result rotation: files >30d deleted, most recent kept | unit | `uv run pytest tests/test_perf.py::test_rotate_old_results -x` | ❌ Wave 0 |
| PERF-04 | Delta computation: elapsed_ms diff vs previous run | unit | `uv run pytest tests/test_perf.py::test_delta_computation -x` | ❌ Wave 0 |
| PERF-05 | GET /perf/results returns date list | unit | `uv run pytest tests/test_api.py::test_perf_list_results -x` | ❌ Wave 0 |
| PERF-06 | GET /perf/results/latest returns latest+previous | unit | `uv run pytest tests/test_api.py::test_perf_latest -x` | ❌ Wave 0 |
| PERF-07 | sb-perf --cleanup purges orphan notes | unit | `uv run pytest tests/test_perf.py::test_cleanup_flag -x` | ❌ Wave 0 |
| PERF-08 | Tool error is recorded, suite continues | unit | `uv run pytest tests/test_perf.py::test_error_recovery -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_perf.py -x -q`
- **Per wave merge:** `uv run pytest tests/test_perf.py tests/test_api.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_perf.py` — covers PERF-01 through PERF-08 (new file)
- [ ] `engine/perf.py` — module must exist before tests import it
- [ ] `engine/test_utils.py` — cleanup utility

*(No framework changes needed — pytest already configured)*

---

## Sources

### Primary (HIGH confidence)
- Direct file reads: `engine/health.py`, `engine/api.py`, `engine/paths.py`, `frontend/src/App.tsx`, `frontend/src/components/TabBar.tsx`, `frontend/src/contexts/UIContext.tsx`, `frontend/src/components/ui/health-score-gauge.tsx`, `frontend/package.json`, `pyproject.toml`, `.planning/phases/45-performance-testing-framework/45-CONTEXT.md`

### Secondary (MEDIUM confidence)
- Python stdlib `time.monotonic()` — documented behavior, no external verification needed
- lucide-react Gauge icon — available in 0.577.0 (verified: library is installed at this version; specific icon presence assumed HIGH given broad icon set)

### Tertiary (LOW confidence)
- recharts not in frontend: verified by direct package.json read (HIGH, not LOW)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified by direct file inspection
- Architecture: HIGH — patterns derived from existing engine/health.py, api.py, App.tsx
- Pitfalls: HIGH — derived from codebase inspection + LEARNINGS.md patterns
- Charting decision: MEDIUM — recharts absence confirmed; SVG sparkline approach is a recommendation, not a locked decision

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable codebase; frontend deps change rarely)
