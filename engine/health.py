"""sb-health — verify all second-brain components are working."""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

def _ok(label: str, detail: str = "") -> dict:
    return {"label": label, "status": "ok", "detail": detail}

def _warn(label: str, detail: str = "") -> dict:
    return {"label": label, "status": "warn", "detail": detail}

def _fail(label: str, detail: str = "") -> dict:
    return {"label": label, "status": "fail", "detail": detail}


# ── checks ────────────────────────────────────────────────────────────────────

def check_brain_directory() -> dict:
    from engine.paths import BRAIN_ROOT
    if not BRAIN_ROOT.exists():
        return _fail("Brain directory", f"{BRAIN_ROOT} not found")
    if not BRAIN_ROOT.is_dir():
        return _fail("Brain directory", f"{BRAIN_ROOT} is not a directory")
    test_file = BRAIN_ROOT / ".health_check_tmp"
    try:
        test_file.touch()
        test_file.unlink()
    except OSError as exc:
        return _fail("Brain directory", f"not writable: {exc}")
    return _ok("Brain directory", str(BRAIN_ROOT))


def check_database() -> dict:
    from engine.paths import DB_PATH
    if not DB_PATH.exists():
        return _fail("SQLite database", f"{DB_PATH} not found — run sb-init")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
    except sqlite3.Error as exc:
        return _fail("SQLite database", str(exc))
    required = {"notes", "notes_fts", "relationships", "audit_log"}
    missing = required - tables
    if missing:
        return _fail("SQLite database", f"missing tables: {', '.join(sorted(missing))}")
    return _ok("SQLite database", str(DB_PATH))


def check_fts_index() -> dict:
    from engine.paths import DB_PATH
    if not DB_PATH.exists():
        return _fail("FTS index", "database not found")
    try:
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        conn.close()
    except sqlite3.Error as exc:
        return _fail("FTS index", str(exc))
    if count == 0:
        return _warn("FTS index", "0 notes indexed — run sb-reindex")
    return _ok("FTS index", f"{count} notes indexed")


def check_embeddings() -> dict:
    import urllib.request, json as _json
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as resp:
            data = _json.loads(resp.read())
        models = [m["name"] for m in data.get("models", [])]
        missing = [m for m in ("nomic-embed-text", "llama3.2") if not any(m in n for n in models)]
        if missing:
            return _warn("Embeddings (Ollama)", f"running but missing models: {', '.join(missing)} — run sb-init")
        return _ok("Embeddings (Ollama)", "running, nomic-embed-text + llama3.2 available")
    except Exception:
        return _warn("Embeddings (Ollama)", "not running — run sb-init to start it")


def check_launchd() -> dict:
    if sys.platform != "darwin":
        return _ok("Launchd watcher", "N/A (not macOS)")
    plist = Path.home() / "Library" / "LaunchAgents" / "com.secondbrain.watch.plist"
    if not plist.exists():
        return _warn("Launchd watcher", "not installed — run sb-install")
    result = subprocess.run(
        ["launchctl", "list", "com.secondbrain.watch"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return _warn("Launchd watcher", "plist exists but service not loaded — run: launchctl load " + str(plist))
    return _ok("Launchd watcher", "com.secondbrain.watch loaded")


def check_mcp_server() -> dict:
    # Check binary exists
    binary = shutil.which("sb-mcp-server")
    if binary is None:
        venv_bin = Path(sys.executable).parent / "sb-mcp-server"
        project_bin = Path(__file__).parent.parent / ".venv" / "bin" / "sb-mcp-server"
        if venv_bin.exists():
            binary = str(venv_bin)
        elif project_bin.exists():
            binary = str(project_bin)
    if binary is None:
        return _fail("MCP server binary", "sb-mcp-server not found — run sb-install")

    # Check Claude Desktop config
    if sys.platform == "darwin":
        cfg_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        cfg_path = None

    if cfg_path and cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if "second-brain" not in cfg.get("mcpServers", {}):
                return _warn("MCP server", f"binary ok but not in Claude Desktop config — run sb-init")
        except json.JSONDecodeError:
            return _warn("MCP server", "Claude Desktop config is malformed")
        return _ok("MCP server", f"registered in Claude Desktop config")
    return _ok("MCP server binary", binary)


def check_git_hooks() -> dict:
    repo_root = Path(__file__).parent.parent
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return _warn("Git hooks", "not a git repository")
    result = subprocess.run(
        ["/usr/bin/git", "-C", str(repo_root), "config", "core.hooksPath"],
        capture_output=True, text=True,
    )
    hooks_path = result.stdout.strip()
    if not hooks_path:
        return _warn("Git hooks", "not configured — run: git config core.hooksPath .githooks")
    return _ok("Git hooks", f"hooksPath = {hooks_path}")


def check_global_cli() -> dict:
    missing = [cmd for cmd in ("sb-search", "sb-capture", "sb-reindex") if shutil.which(cmd) is None]
    if missing:
        return _warn("Global CLI", f"commands not in PATH: {', '.join(missing)} — run sb-install")
    return _ok("Global CLI", "sb-search, sb-capture, sb-reindex in PATH")


def check_pii_processing() -> dict:
    """Send a test prompt with a person's name to llama3.2 and verify it responds."""
    import urllib.request, json as _json
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=2)
    except Exception:
        return _warn("PII processing (llama3.2)", "Ollama not running — run sb-init")

    payload = _json.dumps({
        "model": "llama3.2",
        "prompt": "Reply with only 'ok'. Input: Alice Smith attended a meeting.",
        "stream": False,
        "options": {"num_predict": 10},
    }).encode()
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = _json.loads(resp.read())
        response_text = data.get("response", "").strip()
        if not response_text:
            return _fail("PII processing (llama3.2)", "model returned empty response")
        return _ok("PII processing (llama3.2)", f"llama3.2 responded ({len(response_text)} chars)")
    except Exception as exc:
        return _fail("PII processing (llama3.2)", f"inference failed: {exc}")


# ── runner ────────────────────────────────────────────────────────────────────

CHECKS = [
    check_brain_directory,
    check_database,
    check_fts_index,
    check_global_cli,
    check_git_hooks,
    check_mcp_server,
    check_launchd,
    check_embeddings,
    check_pii_processing,
]

STATUS_ICON = {"ok": "\033[32m✓\033[0m", "warn": "\033[33m⚠\033[0m", "fail": "\033[31m✗\033[0m"}


def _run_brain_health() -> None:
    """Print brain content health score and issue counts, then return."""
    from engine.paths import DB_PATH
    conn = sqlite3.connect(str(DB_PATH))
    try:
        from engine.brain_health import (
            get_orphan_notes,
            get_duplicate_candidates,
            compute_health_score,
        )
        from engine.links import check_links
        from engine.paths import BRAIN_ROOT

        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        orphans = get_orphan_notes(conn)
        broken = check_links(BRAIN_ROOT, conn)
        duplicates = get_duplicate_candidates(conn)
        score = compute_health_score(
            total_notes=total,
            orphans=len(orphans),
            broken=len(broken),
            duplicates=len(duplicates),
        )
        print(f"\nBrain Health Score: {score}/100")
        print(f"Orphan notes:       {len(orphans)}")
        print(f"Broken links:       {len(broken)}")
        print(f"Duplicate pairs:    {len(duplicates)}\n")
    except Exception as exc:
        print(f"Brain health check error: {exc}", file=sys.stderr)
    finally:
        conn.close()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="sb-health", add_help=True)
    parser.add_argument(
        "--brain",
        action="store_true",
        help="Check brain content health (orphans, broken links, duplicates) instead of system health",
    )
    args = parser.parse_args()

    if args.brain:
        _run_brain_health()
        return

    print("\nsb-health — second brain system check\n")

    results = []
    for fn in CHECKS:
        try:
            r = fn()
        except Exception as exc:
            r = _fail(fn.__name__, f"unexpected error: {exc}")
        results.append(r)
        icon = STATUS_ICON[r["status"]]
        detail = f"  {r['detail']}" if r["detail"] else ""
        print(f"  {icon}  {r['label']}{detail}")

    fails = [r for r in results if r["status"] == "fail"]
    warns = [r for r in results if r["status"] == "warn"]

    print()
    if fails:
        print(f"\033[31m{len(fails)} check(s) failed.\033[0m  Run setup.sh or fix issues above.")
        sys.exit(1)
    elif warns:
        print(f"\033[33m{len(warns)} warning(s).\033[0m  System functional; optional components need attention.")
    else:
        print("\033[32mAll checks passed.\033[0m")
    print()
