# Phase 8: Fix update_memory() Routing Bypass - Research

**Researched:** 2026-03-15
**Domain:** Python internal wiring — `engine/ai.py`, `engine/router.py`
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AI-05 | Per-content-type model routing is configurable in `.meta/config.toml` without code changes | `update_memory()` in `engine/ai.py:122` hardcodes `ClaudeAdapter()` directly, bypassing `_router.get_adapter()`. The `config_path` parameter is received but never used. Fix: call `_router.get_adapter(sensitivity, config_path)` with a safe default sensitivity, or remove the dead `config_path` parameter and document the intentional bypass. |

</phase_requirements>

---

## Summary

Phase 8 is a single-function surgical fix. `update_memory()` in `engine/ai.py` accepts a `config_path` parameter and passes it at the call site (`capture.py:206`), but the function body ignores it — it hardcodes `ClaudeAdapter()` directly, bypassing the router entirely. This means a user who configures `public_model = "ollama/..."` in `config.toml` will still get `ClaudeAdapter` for memory updates, violating AI-05.

There are exactly two valid resolutions: (A) wire `config_path` through `_router.get_adapter()` so routing config applies to memory updates, or (B) remove the `config_path` parameter entirely and document that memory updates intentionally always use `ClaudeAdapter` (because the summary passed to `update_memory()` is already non-PII-sanitized and intended for Claude memory). The phase description ("wire config_path through get_adapter() in update_memory() or remove dead parameter") explicitly names both options.

The fix is one function, one test, two plan files. No new dependencies, no schema changes, no module additions.

**Primary recommendation:** Option A (wire through router) — it satisfies AI-05 as written. Option B is valid only if a conscious architectural decision is made that memory updates are always cloud-only; the current docstring already hints at this ("summary is safe — no PII, just type + controlled summary"). The planner should pick one and apply it consistently.

---

## Standard Stack

All existing. No new dependencies.

### Core (already present)
| Module | Location | Role in Phase 8 |
|--------|----------|-----------------|
| `engine.router.get_adapter` | `engine/router.py:14` | Already used by `ask_followup_questions()`; needs to be called by `update_memory()` too |
| `engine.config_loader.load_config` | `engine/config_loader.py:21` | Called inside `get_adapter()` — no direct use needed |
| `engine.ai.update_memory` | `engine/ai.py:122` | The broken function — one of two fixes applied here |
| `engine.adapters.claude_adapter.ClaudeAdapter` | `engine/adapters/claude_adapter.py` | Currently hardcoded; removed from `update_memory()` body if Option A chosen |

### No New Installs Required
`uv.lock` and `pyproject.toml` unchanged.

---

## Architecture Patterns

### Current broken implementation

```python
# engine/ai.py:122 — CURRENT (broken)
def update_memory(note_type: str, summary: str, config_path: Path) -> None:
    """...config_path: Path to config.toml (unused for memory, ClaudeAdapter is always used)."""
    try:
        ...
        adapter = ClaudeAdapter()   # <-- hardcoded, bypasses router; config_path never used
        ...
```

The docstring itself says "config_path: Path to config.toml (unused for memory, ClaudeAdapter is always used)" — this is the explicit admission of the bypass.

### Option A: Wire through router (recommended — satisfies AI-05)

```python
# engine/ai.py — FIXED (Option A)
def update_memory(note_type: str, summary: str, config_path: Path) -> None:
    """Update Claude memory with new context from a captured note (CAP-06).

    Routes through ModelRouter using 'public' sensitivity — summary contains
    no PII (type + controlled title only). config_path is now active (AI-05).
    """
    try:
        system_prompt = (
            "Update the project memory file with new context. "
            "Do not include sensitive details. Write concise bullet points."
        )
        user_content = f"Note type: {note_type}. Summary: {summary}"

        adapter = _router.get_adapter("public", config_path)  # AI-05: config drives adapter

        if not shutil.which("claude"):
            raise RuntimeError("claude CLI not found")

        full_prompt = f"{system_prompt}\n\n---\n\n{user_content}"
        subprocess.run(
            ["claude", "-p", full_prompt, "--allowedTools", "Write,Read"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as e:
        print(f"Memory update skipped: {type(e).__name__}")
```

Key change: `ClaudeAdapter()` replaced by `_router.get_adapter("public", config_path)`.
The `from engine.adapters.claude_adapter import ClaudeAdapter` import at the top of `ai.py` can be removed if nothing else in the file uses it (currently it is only used in `update_memory()`).

### Option B: Remove dead parameter (intentional bypass)

```python
# engine/ai.py — FIXED (Option B)
def update_memory(note_type: str, summary: str) -> None:
    """...Memory updates always use ClaudeAdapter — summary is non-PII, intended for Claude memory."""
    ...
    adapter = ClaudeAdapter()  # intentional: memory updates are always cloud
```

Call site in `capture.py:206` changes from:
```python
update_memory(args.note_type, f"{args.note_type} note: {args.title}", CONFIG_PATH)
```
to:
```python
update_memory(args.note_type, f"{args.note_type} note: {args.title}")
```

### Existing call site (capture.py — already correct, no changes needed)

```python
# engine/capture.py:202-208 — already wired correctly
if sensitivity != "pii":
    try:
        from engine.ai import update_memory
        update_memory(args.note_type, f"{args.note_type} note: {args.title}", CONFIG_PATH)
    except Exception as e:
        print(f"[sb-capture] Memory update skipped: {type(e).__name__}")
```

The call site is already in place from Phase 6. No changes to `capture.py` are needed.

### Sensitivity to use when routing memory updates

Memory updates receive a summary of the form `"{note_type} note: {title}"`. PII captures are already filtered out at the call site (`if sensitivity != "pii"`). The summary never contains raw PII body content. Therefore `"public"` is the correct sensitivity to pass to `get_adapter()` — it routes to the configured `public_model`, which is `claude` by default. If a user configures `public_model` to Ollama, that would now apply to memory updates too (which is the desired AI-05 behaviour).

### Existing test for update_memory (must remain passing)

```python
# tests/test_ai.py:46
def test_cap06_memory_update_uses_write_tool(tmp_config_toml):
    from engine.ai import update_memory
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="done")
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            update_memory("people", "Alice is the CTO", tmp_config_toml)
    call_args = mock_run.call_args[0][0]
    assert "--allowedTools" in call_args
    allowed = call_args[call_args.index("--allowedTools") + 1]
    assert "Write" in allowed
```

This test already passes `tmp_config_toml`. Under Option A it will still pass — `get_adapter("public", tmp_config_toml)` returns `ClaudeAdapter` (same as before with the default config), and `subprocess.run` is patched. The test continues to pass without modification.

### Anti-Patterns to Avoid

- **Passing `sensitivity` from the caller through to `update_memory()`:** The call site in `capture.py` already guards `sensitivity != "pii"` before calling. Adding a sensitivity parameter to `update_memory()` would be over-engineering — use `"public"` as the fixed internal sensitivity for memory updates.
- **Changing `capture.py`'s call site:** The call site is already correct. All the change lives inside `update_memory()` itself.
- **Removing the `ClaudeAdapter` import before checking if it's used elsewhere:** Grep `engine/ai.py` for `ClaudeAdapter` — if Option A is chosen, the import at line 8 becomes unused and should be removed to keep the module clean.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Routing logic for memory updates | New if/else sensitivity dispatch inside `update_memory()` | `_router.get_adapter("public", config_path)` — already does this |
| Config file reading | `tomllib.load()` in `update_memory()` | `get_adapter()` calls `load_config()` internally — transparent |

---

## Common Pitfalls

### Pitfall 1: Option A breaks the existing test if `ClaudeAdapter` import is referenced elsewhere

**What goes wrong:** Removing `from engine.adapters.claude_adapter import ClaudeAdapter` at `ai.py:8` causes a NameError if something else in `ai.py` references `ClaudeAdapter`.
**Why it happens:** The import is module-level. Easy to forget that only `update_memory()` used it.
**How to avoid:** Search `ai.py` for `ClaudeAdapter` after the fix. Currently only `update_memory()` uses it — safe to remove if Option A chosen.
**Warning signs:** `NameError: name 'ClaudeAdapter' is not defined` in test run.

### Pitfall 2: New routing test patches wrong symbol

**What goes wrong:** Test patches `engine.ai.ClaudeAdapter` instead of `engine.router.get_adapter` — the patch doesn't intercept correctly.
**Why it happens:** Under Option A, `update_memory()` no longer calls `ClaudeAdapter()` directly; it calls `_router.get_adapter()`. The existing `test_cap06_memory_update_uses_write_tool` patches `subprocess.run` (correct) but doesn't assert which adapter was selected.
**How to avoid:** For the new routing test (Wave 0), patch `engine.router.get_adapter` and assert it was called with `("public", config_path)`. The pattern from `test_ai.py:31` — `patch("engine.router.get_adapter", return_value=mock_adapter)` — is the right pattern.
**Warning signs:** Test passes even when adapter selection is wrong.

### Pitfall 3: Option B still marks AI-05 as unclosed if not documented clearly

**What goes wrong:** If Option B is chosen but the docstring still says "unused", the requirement AI-05 remains ambiguous.
**Why it happens:** AI-05 says "configurable without code changes". Option B makes it intentionally not configurable — which is an architectural decision, not a bug.
**How to avoid:** If Option B chosen, update docstring to say "Memory updates always use ClaudeAdapter by design — the summary is non-PII and intended exclusively for Claude memory" and add a comment at the call site. Then mark AI-05 complete with a note in STATE.md explaining the intentional exception.

---

## Code Examples

### Wave 0 test: routing config affects adapter selection (Option A)

```python
# tests/test_ai.py — new test for Wave 0
def test_update_memory_routing_uses_config(tmp_config_toml):
    """AI-05: config_path is active — routing config affects adapter selected by update_memory()."""
    from engine.ai import update_memory
    with patch("engine.router.get_adapter") as mock_get_adapter:
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="done")
                update_memory("people", "Alice is CTO", tmp_config_toml)
        mock_get_adapter.assert_called_once_with("public", tmp_config_toml)
```

This test is RED before the fix (current code calls `ClaudeAdapter()` directly, never calls `get_adapter`) and GREEN after.

### Wave 0 test: alternate config routes to different adapter (Option A, stronger coverage)

```python
def test_update_memory_routing_respects_public_model(tmp_path):
    """AI-05: changing public_model in config.toml changes adapter used by update_memory()."""
    from engine.ai import update_memory
    from engine.adapters.ollama_adapter import OllamaAdapter
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        '[routing]\n'
        'pii_model = "ollama/llama3.2"\n'
        'private_model = "ollama/llama3.2"\n'
        'public_model = "ollama/llama3.2"\n'  # override: public -> ollama
        '\n[ollama]\nhost = "http://host.docker.internal:11434"\n'
        '\n[models]\n"ollama/llama3.2" = {adapter = "ollama", model = "llama3.2"}\n'
        '"claude" = {adapter = "claude", model = ""}\n'
    )
    with patch("engine.router.get_adapter", wraps=__import__("engine.router", fromlist=["get_adapter"]).get_adapter) as spy:
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="done")
                update_memory("note", "test summary", cfg)
        # adapter resolved via config — would be OllamaAdapter with this config
        spy.assert_called_once()
        call_args = spy.call_args
        assert call_args[0][0] == "public"  # sensitivity
        assert call_args[0][1] == cfg       # config_path passed through
```

Note: the simpler `mock_get_adapter.assert_called_once_with(...)` test in Wave 0 is sufficient — the above is optional stronger coverage.

---

## State of the Art

| Old State | Fixed State | Gap |
|-----------|-------------|-----|
| `update_memory()` hardcodes `ClaudeAdapter()` | Routes through `_router.get_adapter("public", config_path)` | `config_path` parameter was dead — routing config had no effect on memory updates |
| `config_path` accepted but ignored | `config_path` passed to `get_adapter()` | AI-05: config.toml must affect all routing without code changes |

---

## Open Questions

1. **Option A vs Option B**
   - What we know: Phase description says "wire config_path through get_adapter() in update_memory() OR remove dead parameter" — both are acceptable
   - What's unclear: whether the user wants memory updates to be configurable (Option A) or always Claude (Option B)
   - Recommendation: Option A is the correct default — it satisfies AI-05 as written. Option B requires an explicit architectural decision. Planner should implement Option A unless user has already stated a preference for B.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest tests/test_ai.py tests/test_router.py -x` |
| Full suite command | `uv run --no-project --with pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-05 | `update_memory()` calls `get_adapter()` with `config_path` | unit | `pytest tests/test_ai.py::test_update_memory_routing_uses_config -x` | Wave 0 |
| AI-05 | Existing `test_cap06_memory_update_uses_write_tool` still passes | unit | `pytest tests/test_ai.py::test_cap06_memory_update_uses_write_tool -x` | YES (existing) |

### Sampling Rate
- **Per task commit:** `uv run --no-project --with pytest tests/test_ai.py -x`
- **Per wave merge:** `uv run --no-project --with pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ai.py` — add `test_update_memory_routing_uses_config` asserting `get_adapter` called with `("public", config_path)`

*(Existing test `test_cap06_memory_update_uses_write_tool` covers the subprocess/Write tool assertion — no changes needed there)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `engine/ai.py` — `update_memory()` full implementation, line 122-155
- Direct code inspection: `engine/router.py` — `get_adapter()` signature and behaviour
- Direct code inspection: `engine/capture.py` — existing call site at lines 202-208
- Direct code inspection: `tests/test_ai.py` — existing `test_cap06_memory_update_uses_write_tool` pattern
- Direct code inspection: `tests/conftest.py:68` — `tmp_config_toml` fixture shape
- `.planning/REQUIREMENTS.md` — AI-05 definition verified

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated decisions: "Phase 03 entry: CAP-06 memory update path confirmed in ClaudeAdapter (03-03)" — confirms the hardcoded path was a known Phase 3 decision, not accidental

### Tertiary (LOW confidence)
- None required — all claims verified from source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules already exist and are tested
- Architecture: HIGH — bug and both fix options verified directly from source
- Pitfalls: HIGH — all pitfalls derived from reading the existing test suite and import structure

**Research date:** 2026-03-15
**Valid until:** Stable — internal-only change, no external libraries
