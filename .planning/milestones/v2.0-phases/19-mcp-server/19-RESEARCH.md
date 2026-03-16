# Phase 19: MCP Server - Research

**Researched:** 2026-03-15
**Domain:** FastMCP stdio server, MCP protocol, Python tool decoration, Claude Desktop config
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCP-01 | User can connect brain to Claude Desktop and Claude.ai via `sb-mcp-server` | FastMCP stdio server registered as pyproject.toml entry point; Claude Desktop reads `claude_desktop_config.json` |
| MCP-02 | `sb-init` auto-writes Claude Desktop MCP config | Config path is `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS; JSON-merge pattern documented |
| MCP-03 | MCP exposes full feature parity with GUI — search, capture, read, edit, create, forget, recap, digest, connections, action items, file listing | All target functions exist in engine modules; thin wrapper pattern applies |
| MCP-04 | Destructive tools (`sb-forget`, `sb-anonymize`) require two-step confirmation with 60-second token | In-memory token store with `time.time()` expiry; confirm parameter on second call |
| MCP-05 | PII routing inherited from existing ModelRouter — no new bypass | `engine/router.py` `get_adapter()` called unchanged from MCP tool handlers |
| MCP-06 | MCP server returns structured errors with error codes — never silently fails | Raise `ValueError`/custom exception from tool; FastMCP serializes to structured `isError: true` response |
| MCP-07 | All MCP tool inputs are validated before execution (type, path, size limits) | Pydantic type annotations on tool parameters auto-validate via FastMCP; explicit guard clauses for path traversal and size |
| MCP-08 | Transient failures retry with exponential backoff | `tenacity` library `@retry(wait=wait_exponential(...), retry=retry_if_exception_type(...))` |
| MCP-09 | Every tool call is recorded in the audit log | Call `log_audit(conn, "mcp_<tool>", path)` from existing `engine.capture.log_audit` |
| MCP-10 | Write tools are idempotent — duplicate `sb_capture` with identical content creates no duplicate note | Content-hash check before `write_note_atomic`; return existing note path if hash matches |
</phase_requirements>

---

## Summary

Phase 19 adds a FastMCP stdio server (`engine/mcp_server.py`) that wraps the existing engine modules directly — no HTTP sidecar involved. The MCP server is registered as a `sb-mcp-server` entry point in `pyproject.toml` and runs as a stdio process launched by Claude Desktop or Claude.ai.

The primary technical work is (1) defining ~12 FastMCP tools as thin wrappers over existing engine functions, (2) implementing a 60-second token store for destructive-operation confirmation, (3) ensuring idempotency for `sb_capture` via content-hash dedup, and (4) extending `sb-init` to write the `claude_desktop_config.json` entry automatically.

All PII routing, audit logging, and error handling follow patterns already established in the codebase — the MCP layer adds no new infrastructure, only a new invocation surface.

**Primary recommendation:** Use `fastmcp` (PyPI: `fastmcp>=2.0`) as the server framework, register tools with `@mcp.tool()` decorators, run with `mcp.run(transport="stdio")` as the entry point, and keep each tool body under 30 lines by delegating immediately to existing engine functions.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastmcp | >=2.0 (latest: 3.1.1 as of 2026-03-14) | MCP server framework, tool decoration, stdio transport | Powers 70% of MCP servers; actively maintained; cleaner API than raw `mcp` SDK |
| tenacity | >=8.0 | Retry with exponential backoff | Industry standard for Python retry logic; used across the AI/LLM toolchain |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| mcp (official SDK) | >=1.0 | Protocol types, `McpError` | Import error types and protocol constants only; FastMCP wraps the SDK |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fastmcp | raw mcp SDK | More boilerplate; FastMCP IS the idiomatic Python choice |
| tenacity | manual retry loop | Tenacity handles jitter, logging, and exception type filtering cleanly |

**Installation:**
```bash
uv add fastmcp tenacity
```

---

## Architecture Patterns

### Recommended Project Structure

```
engine/
├── mcp_server.py       # FastMCP server definition — all @mcp.tool() decorators
└── _mcp_tokens.py      # In-memory token store for destructive confirmation (optional: inline in mcp_server.py)
tests/
└── test_mcp.py         # Unit tests for each tool via FastMCP test client
```

### Pattern 1: FastMCP stdio server entry point

**What:** Create a `FastMCP` instance, decorate functions as tools, run in stdio mode.
**When to use:** All MCP servers destined for Claude Desktop / Claude.ai.

```python
# engine/mcp_server.py
from fastmcp import FastMCP

mcp = FastMCP("second-brain")

@mcp.tool()
def sb_search(query: str, limit: int = 10) -> list[dict]:
    """Search brain notes by keyword and semantic similarity."""
    from engine.db import get_connection
    from engine.search import search_notes
    conn = get_connection()
    try:
        return search_notes(conn, query, limit=limit)
    finally:
        conn.close()

def main():
    mcp.run(transport="stdio")
```

`pyproject.toml`:
```toml
sb-mcp-server = "engine.mcp_server:main"
```

### Pattern 2: Two-step destructive confirmation with token

**What:** First call returns a token; second call within 60 seconds with the token executes.
**When to use:** `sb_forget` and `sb_anonymize` tools.

```python
# Source: custom pattern — no library needed
import secrets
import time

_pending: dict[str, float] = {}  # token -> expiry

def _issue_token() -> str:
    tok = secrets.token_hex(16)
    _pending[tok] = time.time() + 60
    return tok

def _consume_token(tok: str) -> bool:
    expiry = _pending.pop(tok, None)
    return expiry is not None and time.time() < expiry

@mcp.tool()
def sb_forget(slug: str, confirm_token: str = "") -> dict:
    """Forget a person. Call once to get a token; call again with token within 60s to execute."""
    if not confirm_token:
        token = _issue_token()
        return {"status": "pending", "confirm_token": token,
                "message": f"Call sb_forget again with confirm_token='{token}' within 60 seconds."}
    if not _consume_token(confirm_token):
        raise ValueError("TOKEN_EXPIRED: confirm_token is invalid or expired. Call sb_forget without a token to get a new one.")
    # proceed with forget
    from engine.db import get_connection
    from engine.forget import forget_person
    from engine.paths import BRAIN_ROOT
    conn = get_connection()
    try:
        result = forget_person(slug, BRAIN_ROOT, conn)
        _log_mcp_audit("mcp_forget", slug)
        return result
    finally:
        conn.close()
```

### Pattern 3: Idempotent capture via content-hash

**What:** Hash title + body; check notes table before writing. Return existing note if duplicate.
**When to use:** `sb_capture` tool (MCP-10).

```python
import hashlib

def _content_hash(title: str, body: str) -> str:
    return hashlib.sha256(f"{title}\n{body}".encode()).hexdigest()

@mcp.tool()
def sb_capture(title: str, body: str, note_type: str = "note",
               tags: list[str] = [], sensitivity: str = "public") -> dict:
    """Capture a new note. Idempotent — identical title+body returns existing note."""
    from engine.db import get_connection
    conn = get_connection()
    try:
        chash = _content_hash(title, body)
        row = conn.execute(
            "SELECT path FROM notes WHERE title=? AND body=?", (title, body)
        ).fetchone()
        if row:
            return {"status": "exists", "path": row[0]}
        # ... proceed to write_note_atomic
    finally:
        conn.close()
```

### Pattern 4: Structured error responses

**What:** Raise `ValueError` (or a typed exception) with an error code prefix; FastMCP wraps it as `isError: true` with the message text.
**When to use:** All validation failures (MCP-06, MCP-07).

```python
# BAD — silent failure
if not path.exists():
    return {}

# GOOD — structured error that the LLM can reason about
if not path.exists():
    raise ValueError(f"NOTE_NOT_FOUND: {path} does not exist in the brain.")
```

### Pattern 5: Exponential backoff for transient failures

**What:** Wrap engine calls that touch SQLite or Ollama with `@retry`.
**When to use:** Any tool that calls Ollama (`sb_recap`, `sb_digest`) or has DB write contention.

```python
from tenacity import retry, wait_exponential, retry_if_exception_type, stop_after_attempt
import sqlite3

@retry(
    retry=retry_if_exception_type((sqlite3.OperationalError, ConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
)
def _call_with_retry(fn, *args, **kwargs):
    return fn(*args, **kwargs)
```

### Pattern 6: Claude Desktop config auto-write in `sb-init`

**What:** After init completes, write or merge the `mcpServers` entry into `claude_desktop_config.json`.
**When to use:** MCP-02.

```python
import json, platform
from pathlib import Path

def _claude_desktop_config_path() -> Path | None:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if platform.system() == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    return None  # Linux: not supported by Claude Desktop yet

def write_mcp_config(sb_mcp_bin: str) -> None:
    cfg_path = _claude_desktop_config_path()
    if cfg_path is None:
        return
    cfg = {}
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
    cfg.setdefault("mcpServers", {})["second-brain"] = {
        "command": sb_mcp_bin,  # absolute path to sb-mcp-server binary
        "args": []
    }
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print(f"  [MCP] Wrote Claude Desktop config: {cfg_path}")
```

### Anti-Patterns to Avoid

- **Importing from `engine/api.py` in the MCP server:** The MCP server calls engine functions directly; the HTTP sidecar is only for the GUI.
- **Starting the MCP server in SSE/HTTP mode by default:** Claude Desktop requires stdio transport; SSE is only for web-hosted MCP.
- **Raising bare `Exception` from tools:** Always use a typed exception (`ValueError`, `PermissionError`) with a human-readable error code prefix so the LLM can interpret and recover.
- **Mutable default arguments in tool signatures:** `tags: list[str] = []` is a Python gotcha. Use `tags: list[str] | None = None` and coerce to `[]` in the body.
- **Performing blocking Ollama calls without retry:** Ollama can timeout on cold start; wrap in `_call_with_retry`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol framing, JSON-RPC, schema generation | Custom JSON-RPC loop | `fastmcp` | FastMCP handles all wire protocol; 400+ LOC eliminated |
| Exponential backoff with jitter | Manual sleep loop | `tenacity` | Handles jitter, exception filtering, stop conditions correctly |
| Tool input type validation | Custom validation functions | FastMCP + Python type annotations | FastMCP generates JSON Schema from type hints and validates before calling the function |

**Key insight:** The MCP server is a thin decoration layer — every tool body should be < 20 lines, delegating immediately to existing engine functions. Any business logic belongs in the engine, not the MCP layer.

---

## Common Pitfalls

### Pitfall 1: Path traversal in note path inputs

**What goes wrong:** An MCP client passes `../../etc/passwd` as a note path; the tool reads it.
**Why it happens:** MCP tools are callable by the LLM which may hallucinate paths.
**How to avoid:** Resolve all incoming paths and assert they are under `BRAIN_ROOT` before any file operation.
```python
def _safe_path(raw: str) -> Path:
    p = Path(raw).resolve()
    if not str(p).startswith(str(BRAIN_ROOT)):
        raise ValueError(f"PATH_OUTSIDE_BRAIN: {raw}")
    return p
```
**Warning signs:** Tool accepts `str` path without resolution.

### Pitfall 2: MCP server stdout pollution breaks stdio transport

**What goes wrong:** Any `print()` statement in the server process writes to stdout, corrupting the JSON-RPC framing.
**Why it happens:** stdio MCP transport uses stdout exclusively for protocol messages.
**How to avoid:** Route all logging to `sys.stderr` or a file. Never call `print()` in `engine/mcp_server.py` or any module it imports at tool-call time.

### Pitfall 3: Token store not thread-safe

**What goes wrong:** Two concurrent tool calls read/write `_pending` dict simultaneously.
**Why it happens:** FastMCP may use asyncio or threads depending on version.
**How to avoid:** Use `threading.Lock()` around `_pending` reads/writes, or use an `asyncio.Lock()` if the server runs in async mode.

### Pitfall 4: Claude Desktop not reloading config

**What goes wrong:** `sb-init` writes the config but Claude Desktop doesn't pick it up.
**Why it happens:** Claude Desktop reads `claude_desktop_config.json` only on startup.
**How to avoid:** Print a clear message: "Restart Claude Desktop to activate the MCP server."

### Pitfall 5: `sb-mcp-server` binary path in config must be absolute

**What goes wrong:** Config uses `sb-mcp-server` bare name; Claude Desktop can't find it in PATH.
**Why it happens:** Claude Desktop launches processes without inheriting the shell PATH.
**How to avoid:** Resolve the binary with `shutil.which("sb-mcp-server")` and write the absolute path.

### Pitfall 6: Duplicate `sb_capture` on retry

**What goes wrong:** Network glitch causes Claude to retry `sb_capture`; two identical notes created.
**Why it happens:** No idempotency check before `write_note_atomic`.
**How to avoid:** Content-hash check (title + body) before inserting — if row exists, return existing path (MCP-10).

---

## Code Examples

Verified patterns from official sources:

### Minimal FastMCP server with stdio transport

```python
# Source: https://gofastmcp.com/deployment/running-server
from fastmcp import FastMCP

mcp = FastMCP("second-brain")

@mcp.tool()
def sb_search(query: str, limit: int = 10) -> list[dict]:
    """Search brain notes."""
    ...

def main():
    mcp.run(transport="stdio")  # stdio is also the default when no transport arg
```

### Tool that returns structured error

```python
# Source: FastMCP docs — raise exception to signal error
@mcp.tool()
def sb_read(path: str) -> dict:
    """Read a note by absolute path."""
    p = _safe_path(path)
    if not p.exists():
        raise ValueError(f"NOTE_NOT_FOUND: {path}")
    return {"content": p.read_text(encoding="utf-8"), "path": str(p)}
```

### Tenacity retry decorator

```python
# Source: https://tenacity.readthedocs.io/
from tenacity import retry, wait_exponential, retry_if_exception_type, stop_after_attempt

@retry(
    retry=retry_if_exception_type((sqlite3.OperationalError, ConnectionError)),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _resilient_call(fn, *args, **kwargs):
    return fn(*args, **kwargs)
```

### claude_desktop_config.json format

```json
{
  "mcpServers": {
    "second-brain": {
      "command": "/Users/username/.local/bin/sb-mcp-server",
      "args": []
    }
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw `mcp` SDK with manual schemas | `fastmcp` decorator pattern | 2024 (FastMCP 1.0 merged into official SDK) | Tool definition reduced from ~50 LOC to ~5 LOC per tool |
| SSE transport for desktop MCP | stdio transport | MCP spec launch | Claude Desktop only supports stdio for local servers |
| Manual JSON config editing | `sb-init` auto-writes `claude_desktop_config.json` | MCP-02 requirement | Zero-config onboarding |

**Deprecated/outdated:**
- `mcp.server.Server` with manual `list_tools`/`call_tool` handlers: replaced by FastMCP decorators.
- SSE transport for local desktop use: stdio is the correct transport; SSE is for remote/hosted servers.

---

## Open Questions

1. **FastMCP async vs sync mode**
   - What we know: FastMCP 2.x+ supports both; `mcp.run()` defaults to sync for simple tools.
   - What's unclear: Whether Ollama calls require async to avoid blocking the event loop.
   - Recommendation: Start with sync tools; if Ollama blocking becomes a problem, use `asyncio.to_thread()` in the tool body.

2. **Claude.ai (web) MCP support**
   - What we know: Claude.ai has MCP support via remote connections; local stdio servers are desktop-only.
   - What's unclear: Whether Claude.ai can connect to a local stdio server via a bridge, or if MCP-01 is scoped to Claude Desktop only.
   - Recommendation: Scope MCP-01 to Claude Desktop for v2.0; Claude.ai compatibility is a v3.0 concern.

3. **`sb-init` platform check for config write**
   - What we know: Claude Desktop config paths differ on macOS and Windows; Linux has no Claude Desktop.
   - What's unclear: Whether `sb-init` should silently skip on Linux or warn.
   - Recommendation: Skip silently on Linux (no Claude Desktop); write config on macOS and Windows only.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (pinned in pyproject.toml `[project.optional-dependencies].dev`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` |
| Quick run command | `pytest tests/test_mcp.py -x -q` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCP-01 | `sb_search` tool callable via MCP | unit | `pytest tests/test_mcp.py::test_sb_search -x` | ❌ Wave 0 |
| MCP-02 | `sb-init` writes `claude_desktop_config.json` | unit | `pytest tests/test_mcp.py::test_init_writes_mcp_config -x` | ❌ Wave 0 |
| MCP-03 | All 12 tools present and callable | unit | `pytest tests/test_mcp.py::test_tool_parity -x` | ❌ Wave 0 |
| MCP-04 | Destructive tool requires token; single call no-ops | unit | `pytest tests/test_mcp.py::test_two_step_confirmation -x` | ❌ Wave 0 |
| MCP-04 | Token expires after 60s | unit | `pytest tests/test_mcp.py::test_token_expiry -x` | ❌ Wave 0 |
| MCP-05 | PII notes routed through Ollama adapter | unit (mock) | `pytest tests/test_mcp.py::test_pii_routing -x` | ❌ Wave 0 |
| MCP-06 | Tool returns structured error on bad input | unit | `pytest tests/test_mcp.py::test_structured_error -x` | ❌ Wave 0 |
| MCP-07 | Path outside BRAIN_ROOT raises error | unit | `pytest tests/test_mcp.py::test_path_traversal_rejected -x` | ❌ Wave 0 |
| MCP-08 | SQLite OperationalError triggers retry | unit (mock) | `pytest tests/test_mcp.py::test_retry_on_db_locked -x` | ❌ Wave 0 |
| MCP-09 | Tool call written to audit_log | unit | `pytest tests/test_mcp.py::test_audit_log_written -x` | ❌ Wave 0 |
| MCP-10 | Duplicate capture returns existing note | unit | `pytest tests/test_mcp.py::test_capture_idempotent -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_mcp.py -x -q`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_mcp.py` — test stubs for all 11 behaviors above (MCP-01 through MCP-10)
- [ ] `engine/mcp_server.py` — stub with `FastMCP("second-brain")` and empty tool stubs
- [ ] Framework install: `uv add fastmcp tenacity` — neither present in `pyproject.toml` yet

---

## Sources

### Primary (HIGH confidence)

- [fastmcp PyPI](https://pypi.org/project/fastmcp/) — version 3.1.1 confirmed current as of 2026-03-14
- [FastMCP GitHub (jlowin/fastmcp)](https://github.com/jlowin/fastmcp) — tool definition, stdio transport, mcp.run()
- [MCP official Python SDK](https://github.com/modelcontextprotocol/python-sdk) — protocol types
- [MCP connect-local-servers docs](https://modelcontextprotocol.io/docs/develop/connect-local-servers) — claude_desktop_config.json format
- [tenacity docs](https://tenacity.readthedocs.io/) — retry/backoff API

### Secondary (MEDIUM confidence)

- [FastMCP running-server guide](https://gofastmcp.com/deployment/running-server) — stdio transport confirmation
- [FastMCP tools reference](https://gofastmcp.com/servers/tools) — tool decoration, error handling
- [Claude Desktop MCP getting started](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) — config path on macOS/Windows

### Tertiary (LOW confidence)

- WebSearch: two-step confirmation pattern — no authoritative library; custom implementation recommended

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — FastMCP is the official recommended framework, versions verified on PyPI
- Architecture: HIGH — patterns derived from official FastMCP docs and existing engine module signatures
- Pitfalls: MEDIUM — stdout pollution and path traversal verified; token thread-safety is LOW (implementation detail)
- Validation architecture: HIGH — existing pytest infrastructure confirmed, test file list derived from requirements

**Research date:** 2026-03-15
**Valid until:** 2026-04-15 (FastMCP is fast-moving; verify fastmcp version before install)
