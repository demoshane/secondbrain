"""sb-perf — performance benchmark runner for MCP tools.

Benchmarks all MCP tools via direct Python import (no transport overhead),
stores timestamped results in PERF_DIR, computes deltas, and prints a
terminal table.  Always exits 0 — a slow tool is a warning, not a failure.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import sys
import time
from pathlib import Path

from engine.paths import META_DIR

PERF_DIR: Path = META_DIR / "perf_results"

# Soft limits (milliseconds) per D-02
SOFT_LIMITS: dict[str, int] = {
    # Read-only tools
    "sb_search": 2000,
    "sb_read": 2000,
    "sb_files": 2000,
    "sb_connections": 2000,
    "sb_actions": 2000,
    "sb_list_persons": 2000,
    "sb_person_context": 2000,
    "sb_tag": 2000,
    "sb_tools": 2000,
    # Write-path tools
    "sb_capture": 5000,
    "sb_capture_batch": 5000,
    "sb_edit": 5000,
    "sb_forget": 5000,
    "sb_anonymize": 5000,
    "sb_link": 5000,
    "sb_unlink": 5000,
    "sb_remind": 5000,
    # AI-heavy tools
    "sb_recap": 20000,
    "sb_digest": 30000,
    # HTTP sidecar
    "ask_brain": 5000,
}


# ── result storage ─────────────────────────────────────────────────────────────

def save_result(data: dict) -> Path:
    """Write *data* as YYYY-MM-DD.json inside PERF_DIR. Overwrites if exists."""
    PERF_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.date.today().isoformat()
    path = PERF_DIR / f"{date_str}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def rotate_old_results() -> int:
    """Delete result files older than 30 days. Always keeps the most recent file.

    Returns:
        Number of files deleted.
    """
    if not PERF_DIR.exists():
        return 0

    files = sorted(PERF_DIR.glob("*.json"), key=lambda f: f.stem)
    if not files:
        return 0

    cutoff = datetime.date.today() - datetime.timedelta(days=30)
    deleted = 0

    # Always keep the last file (most recent)
    files_to_consider = files[:-1]  # exclude last element

    for f in files_to_consider:
        try:
            file_date = datetime.date.fromisoformat(f.stem)
        except ValueError:
            continue
        if file_date < cutoff:
            f.unlink(missing_ok=True)
            deleted += 1

    return deleted


def load_result(date_str: str) -> dict | None:
    """Return parsed JSON for *date_str* (YYYY-MM-DD), or None if not found."""
    if not PERF_DIR.exists():
        return None
    path = PERF_DIR / f"{date_str}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_result_dates() -> list[str]:
    """Return sorted list of YYYY-MM-DD strings from PERF_DIR."""
    if not PERF_DIR.exists():
        return []
    return sorted(f.stem for f in PERF_DIR.glob("*.json"))


def get_result_by_date(date_str: str) -> dict | None:
    """Alias for load_result()."""
    return load_result(date_str)


def get_latest_with_previous() -> dict:
    """Return the two most recent results as {"latest": ..., "previous": ...}.

    Either value is None when not enough files exist.
    """
    dates = list_result_dates()
    if not dates:
        return {"latest": None, "previous": None}
    latest = load_result(dates[-1])
    previous = load_result(dates[-2]) if len(dates) >= 2 else None
    return {"latest": latest, "previous": previous}


# ── delta / status computation ─────────────────────────────────────────────────

def _determine_status(elapsed_ms: float, limit_ms: int, error: str | None) -> str:
    if error:
        return "error"
    if elapsed_ms > limit_ms:
        return "warn"
    return "pass"


def compute_delta(latest: dict, previous: dict | None) -> list[dict]:
    """Compute per-tool delta between *latest* and *previous* result dicts.

    Returns a list of dicts:
        {tool, latest_ms, previous_ms, delta_ms, limit_ms, status}
    previous_ms and delta_ms are None when no previous result exists.
    """
    prev_map: dict[str, dict] = {}
    if previous:
        for tr in previous.get("tool_results", []):
            prev_map[tr["tool"]] = tr

    deltas = []
    for tr in latest.get("tool_results", []):
        tool = tr["tool"]
        latest_ms = tr.get("elapsed_ms", 0.0)
        limit_ms = tr.get("limit_ms", SOFT_LIMITS.get(tool, 5000))
        error = tr.get("error")
        status = _determine_status(latest_ms, limit_ms, error)

        prev_tr = prev_map.get(tool)
        previous_ms = prev_tr["elapsed_ms"] if prev_tr else None
        delta_ms = (latest_ms - previous_ms) if previous_ms is not None else None

        deltas.append({
            "tool": tool,
            "latest_ms": latest_ms,
            "previous_ms": previous_ms,
            "delta_ms": delta_ms,
            "limit_ms": limit_ms,
            "status": status,
        })
    return deltas


# ── benchmark runner ───────────────────────────────────────────────────────────

def _time_tool(fn, *args, **kwargs) -> tuple[float, str | None]:
    """Time a single tool call.  Handles both sync and async functions.

    Returns:
        (elapsed_ms, error_or_None)
    """
    start = time.monotonic()
    try:
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn(*args, **kwargs))
        else:
            fn(*args, **kwargs)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        return elapsed_ms, None
    except Exception as exc:
        elapsed_ms = (time.monotonic() - start) * 1000.0
        return elapsed_ms, str(exc)


def _make_result(tool: str, elapsed_ms: float, error: str | None) -> dict:
    limit_ms = SOFT_LIMITS.get(tool, 5000)
    return {
        "tool": tool,
        "elapsed_ms": round(elapsed_ms, 1),
        "limit_ms": limit_ms,
        "status": _determine_status(elapsed_ms, limit_ms, error),
        "error": error,
    }


def _benchmark_read_tools() -> list[dict]:
    """Benchmark read-only MCP tools via direct Python import."""
    from engine.mcp_server import (  # noqa: PLC0415
        sb_search, sb_read, sb_files, sb_connections,
        sb_actions, sb_list_persons, sb_person_context,
        sb_tag, sb_tools,
    )
    from engine.db import get_connection

    # Find a real note path for tools that require one
    conn = get_connection()
    try:
        row = conn.execute("SELECT path FROM notes LIMIT 1").fetchone()
        note_path = row[0] if row else "notes/test.md"
        person_row = conn.execute(
            "SELECT path FROM notes WHERE type='person' LIMIT 1"
        ).fetchone()
        person_path = person_row[0] if person_row else None
    finally:
        conn.close()

    results = []

    tools_to_run = [
        ("sb_search", sb_search, ("test",), {}),
        ("sb_read", sb_read, (note_path,), {}),
        ("sb_files", sb_files, ("",), {}),
        ("sb_connections", sb_connections, (note_path,), {}),
        ("sb_actions", sb_actions, (), {}),
        ("sb_list_persons", sb_list_persons, (), {}),
        ("sb_tools", sb_tools, (), {}),
        ("sb_tag", sb_tag, (note_path, "remove", "__perf_test_noop__"), {}),
    ]
    if person_path:
        tools_to_run.append(("sb_person_context", sb_person_context, (person_path,), {}))

    for tool_name, fn, args, kwargs in tools_to_run:
        elapsed_ms, error = _time_tool(fn, *args, **kwargs)
        results.append(_make_result(tool_name, elapsed_ms, error))

    return results


def _benchmark_write_tools() -> list[dict]:
    """Benchmark write-path MCP tools, using __perf_test__ fixture notes."""
    from engine.mcp_server import (  # noqa: PLC0415
        sb_capture, sb_capture_batch, sb_edit,
        sb_link, sb_unlink, sb_remind,
        sb_forget, sb_anonymize,
    )
    from engine.test_utils import cleanup_test_notes

    # Pre-flight cleanup
    cleanup_test_notes("__perf_test__")

    results = []
    captured_path: str | None = None
    batch_paths: list[str] = []

    # sb_capture
    try:
        elapsed_ms, error = _time_tool(
            sb_capture,
            title="__perf_test__capture",
            body="performance test note",
            note_type="note",
        )
        results.append(_make_result("sb_capture", elapsed_ms, error))
        if not error:
            # Find the note path from DB
            from engine.db import get_connection
            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT path FROM notes WHERE title=? ORDER BY id DESC LIMIT 1",
                    ("__perf_test__capture",),
                ).fetchone()
                captured_path = row[0] if row else None
            finally:
                conn.close()
    except Exception as exc:
        results.append(_make_result("sb_capture", 0, str(exc)))

    # sb_capture_batch
    try:
        batch_items = json.dumps([
            {"title": f"__perf_test__batch{i}", "body": "batch perf test", "note_type": "note"}
            for i in range(3)
        ])
        elapsed_ms, error = _time_tool(sb_capture_batch, items=batch_items)
        results.append(_make_result("sb_capture_batch", elapsed_ms, error))
        if not error:
            from engine.db import get_connection
            conn = get_connection()
            try:
                rows = conn.execute(
                    "SELECT path FROM notes WHERE title LIKE '__perf_test__batch%'"
                ).fetchall()
                batch_paths = [r[0] for r in rows]
            finally:
                conn.close()
    except Exception as exc:
        results.append(_make_result("sb_capture_batch", 0, str(exc)))

    # sb_edit
    if captured_path:
        elapsed_ms, error = _time_tool(
            sb_edit,
            note_path=captured_path,
            body="performance test note — edited",
        )
        results.append(_make_result("sb_edit", elapsed_ms, error))

    # sb_link / sb_unlink — need two note paths
    if len(batch_paths) >= 2:
        elapsed_ms, error = _time_tool(sb_link, source=batch_paths[0], target=batch_paths[1])
        results.append(_make_result("sb_link", elapsed_ms, error))
        if not error:
            elapsed_ms, error = _time_tool(sb_unlink, source=batch_paths[0], target=batch_paths[1])
            results.append(_make_result("sb_unlink", elapsed_ms, error))

    # sb_remind
    if captured_path:
        remind_at = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
        elapsed_ms, error = _time_tool(sb_remind, note_path=captured_path, remind_at=remind_at)
        results.append(_make_result("sb_remind", elapsed_ms, error))

    # sb_forget (two-step token)
    if captured_path:
        try:
            # Step 1: get confirm_token
            token_result = asyncio.run(sb_forget(note_path=captured_path))
            # Extract token from result string
            import re
            match = re.search(r'"confirm_token":\s*"([^"]+)"', str(token_result))
            if match:
                token = match.group(1)
                elapsed_ms, error = _time_tool(sb_forget, note_path=captured_path, confirm_token=token)
                results.append(_make_result("sb_forget", elapsed_ms, error))
        except Exception as exc:
            results.append(_make_result("sb_forget", 0, str(exc)))

    # sb_anonymize (two-step token) — capture a fresh note with PII-like content
    try:
        asyncio.run(sb_capture(
            title="__perf_test__anon",
            body="John Smith attended a meeting at Acme Corp.",
            note_type="note",
        ))
        from engine.db import get_connection
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT path FROM notes WHERE title='__perf_test__anon' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            anon_path = row[0] if row else None
        finally:
            conn.close()

        if anon_path:
            token_result = asyncio.run(sb_anonymize(note_path=anon_path))
            match = re.search(r'"confirm_token":\s*"([^"]+)"', str(token_result))
            if match:
                token = match.group(1)
                elapsed_ms, error = _time_tool(sb_anonymize, note_path=anon_path, confirm_token=token)
                results.append(_make_result("sb_anonymize", elapsed_ms, error))
    except Exception as exc:
        results.append(_make_result("sb_anonymize", 0, str(exc)))

    # Post-run cleanup
    cleanup_test_notes("__perf_test__")

    return results


def _benchmark_ai_tools() -> list[dict]:
    """Benchmark AI-heavy tools."""
    import re as _re  # noqa: F401 — already imported above but re-import for clarity
    from engine.mcp_server import sb_recap, sb_digest  # noqa: PLC0415

    results = []

    elapsed_ms, error = _time_tool(sb_recap, "today")
    results.append(_make_result("sb_recap", elapsed_ms, error))

    elapsed_ms, error = _time_tool(sb_digest, "week")
    results.append(_make_result("sb_digest", elapsed_ms, error))

    # ask_brain via httpx
    try:
        import httpx
        start = time.monotonic()
        try:
            resp = httpx.post(
                "http://127.0.0.1:37491/ask",
                json={"question": "What did I work on today?"},
                timeout=10.0,
            )
            resp.raise_for_status()
            elapsed_ms = (time.monotonic() - start) * 1000.0
            results.append(_make_result("ask_brain", elapsed_ms, None))
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            elapsed_ms = (time.monotonic() - start) * 1000.0
            results.append(_make_result("ask_brain", elapsed_ms, str(exc)))
    except ImportError:
        results.append(_make_result("ask_brain", 0, "httpx not available"))

    return results


def run_benchmarks(tool_filter: str | None = None) -> dict:
    """Run all (or a single filtered) benchmarks.

    Args:
        tool_filter: If set, only the named tool is benchmarked.

    Returns:
        Result dict per D-15: {"run_at": ISO_str, "tool_results": [...]}
    """
    all_results: list[dict] = []

    read_results = _benchmark_read_tools()
    write_results = _benchmark_write_tools()
    ai_results = _benchmark_ai_tools()

    all_results.extend(read_results)
    all_results.extend(write_results)
    all_results.extend(ai_results)

    if tool_filter:
        all_results = [r for r in all_results if r["tool"] == tool_filter]

    return {
        "run_at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tool_results": all_results,
    }


# ── terminal output ────────────────────────────────────────────────────────────

_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_YELLOW = "\033[33m"
_ANSI_RESET = "\033[0m"

_STATUS_ICON = {
    "pass": f"{_ANSI_GREEN}✓{_ANSI_RESET}",
    "warn": f"{_ANSI_YELLOW}⚠{_ANSI_RESET}",
    "error": f"{_ANSI_RED}✗{_ANSI_RESET}",
}


def _print_table(result: dict, previous: dict | None) -> None:
    deltas = compute_delta(result, previous)
    delta_map = {d["tool"]: d for d in deltas}

    print(f"\nsb-perf — performance benchmark\n")
    header = f"{'Tool':<24} {'Latest':>8} {'Previous':>9} {'Delta':>8} {'Limit':>7} Status"
    print(header)
    print("-" * len(header))

    warns = 0
    errors = 0

    for tr in result.get("tool_results", []):
        tool = tr["tool"]
        d = delta_map.get(tool, {})
        latest_ms = tr.get("elapsed_ms", 0.0)
        limit_ms = tr.get("limit_ms", SOFT_LIMITS.get(tool, 5000))
        status = tr.get("status", "pass")
        error = tr.get("error")

        previous_ms = d.get("previous_ms")
        delta_ms = d.get("delta_ms")

        prev_str = f"{previous_ms:.0f}ms" if previous_ms is not None else "--"
        if delta_ms is not None:
            sign = "+" if delta_ms >= 0 else ""
            delta_str = f"{sign}{delta_ms:.0f}ms"
            # Color: red if regression beyond limit, green if improvement
            if delta_ms > 0 and status == "warn":
                delta_colored = f"{_ANSI_RED}{delta_str}{_ANSI_RESET}"
            elif delta_ms < 0:
                delta_colored = f"{_ANSI_GREEN}{delta_str}{_ANSI_RESET}"
            else:
                delta_colored = delta_str
        else:
            delta_colored = "--"

        icon = _STATUS_ICON.get(status, status)
        if status == "warn":
            warns += 1
        elif status == "error":
            errors += 1

        print(
            f"{tool:<24} {latest_ms:>6.0f}ms {prev_str:>9} {delta_colored:>8} "
            f"{limit_ms:>5}ms {icon}"
        )

    total = len(result.get("tool_results", []))
    passes = total - warns - errors
    print(f"\n{total} tools  {passes} passed  {warns} warnings  {errors} errors\n")


# ── CLI entry point ────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="sb-perf",
        description="Benchmark second-brain MCP tools and show performance deltas.",
    )
    parser.add_argument("--tool", metavar="NAME", help="Benchmark a single tool only")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--cleanup", action="store_true", help="Purge orphaned __perf_test__ notes")
    args = parser.parse_args()

    if args.cleanup:
        from engine.test_utils import cleanup_test_notes
        count = cleanup_test_notes("__perf_test__")
        print(f"Cleaned up {count} __perf_test__ note(s).")
        sys.exit(0)

    # Pre-flight
    rotate_old_results()
    from engine.test_utils import cleanup_test_notes
    cleanup_test_notes("__perf_test__")

    result = run_benchmarks(tool_filter=args.tool)
    save_result(result)

    if args.json:
        print(json.dumps(result, indent=2))
        sys.exit(0)

    previous_data = get_latest_with_previous().get("previous")
    _print_table(result, previous_data)
    sys.exit(0)
