# Phase 44: AI Provider Settings — Research

**Researched:** 2026-03-30
**Domain:** AI adapter routing, macOS Keychain (keyring), Groq REST API, Flask config endpoints, React/shadcn Settings UI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** New `engine/adapters/groq_adapter.py` — calls Groq REST API directly (no SDK; use `httpx` or `requests` already in deps). Model: `llama-3.3-70b-versatile`.
- **D-02:** API key retrieved at call time via `keyring.get_password("second-brain", "groq_api_key")`. Never stored in config.toml or on disk.
- **D-03:** `config.toml` gains a `[groq]` section with per-feature boolean toggles: `ask_brain`, `followup_questions`, `digest`, `person_synthesis`. Default: all `false`.
- **D-04:** `config.toml [routing] all_local = false` (default). When `true`, `router.get_adapter()` always returns OllamaAdapter regardless of Groq key or toggles.
- **D-05:** Routing precedence: (1) all_local=true → Ollama; (2) groq.[feature]=true AND key present → Groq (fallback: claude subprocess); (3) existing routing.*_model keys.
- **D-06:** PII-flagged content is ALWAYS local (existing rule, unchanged).
- **D-07:** Switch `pii_model`, `fallback_model`, and the `ollama/llama3.2` model entry in DEFAULT_CONFIG to use `llama3` (8B). Existing config.toml files with `llama3.2` continue working until user saves.
- **D-08:** Three new Flask endpoints: `GET /config/groq` → `{"configured": bool}`, `POST /config/groq` → saves to Keychain, `DELETE /config/groq` → removes from Keychain.
- **D-09:** New `POST /config/groq/test` → reads key, makes minimal Groq API call (GET /openai/v1/models), returns `{"ok": bool, "error": str | null}`. Auto-called after Save.
- **D-10:** New "AI Provider" section in SettingsModal. Groq key field, all-local toggle (Switch), four Groq feature toggles. See 44-UI-SPEC.md for full interaction contract.
- **D-11:** Groq runtime failure → `FallbackAdapter(GroqAdapter, ClaudeAdapter)` — existing pattern.
- **D-12:** `ask_brain` endpoint response includes `{"provider": "fallback"}` when fallback activates. Frontend shows amber toast "Groq unavailable — used fallback model".

### Claude's Discretion

- Exact Tailwind classes for new Settings section (follow existing section style)
- Whether `groq_adapter.py` uses `httpx` (already in project env) or `requests` — pick whichever is in pyproject.toml
- Whether connectivity test endpoint is called automatically on save or requires a separate "Test" button click (recommended: auto on save)
- Whether `FallbackAdapter` needs a callback/flag to signal fallback was used, or whether the endpoint detects it via exception/flag after the call

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 44 adds Groq as a fast AI provider (target: Ask Brain < 20s vs current 30–90s via claude subprocess) and an all-local privacy toggle. The implementation touches five areas: (1) a new `GroqAdapter` calling `https://api.groq.com/openai/v1/chat/completions` via `httpx`; (2) `keyring` for macOS Keychain storage with three new Flask endpoints; (3) `router.py` extended to honour `all_local` and per-feature Groq toggles; (4) `config_loader.py` updated with new defaults and sections; (5) SettingsModal extended with the UI-SPEC-defined "AI Provider" section including `Switch` components (new shadcn component).

All required dependencies are already available: `httpx` 0.28.1 is in the uv project env as a transitive dep; `keyring` is importable in the project env (also transitive, via fastmcp). Neither needs to be added to `pyproject.toml` as a direct dep — but `keyring` should be added explicitly since it is not listed as a direct dependency and its presence is a coincidence of the transitive graph.

The Groq REST API is OpenAI-compatible. Chat completions endpoint: `POST https://api.groq.com/openai/v1/chat/completions`. Connectivity test: `GET https://api.groq.com/openai/v1/models` (lightweight, returns JSON list, valid for key validation). `FallbackAdapter` is reused without modification; the new challenge is signalling back to the Flask layer which provider was actually used.

**Primary recommendation:** Add `keyring` and `httpx` as direct deps in pyproject.toml, implement GroqAdapter using httpx, extend router with a `feature` param, wire FallbackAdapter for Groq→Claude fallback, expose provider name in ask_brain response.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | 0.28.1 (already in env) | HTTP client for Groq REST API | Modern sync/async, already in project env as transitive dep |
| `keyring` | 25.7.0 (already in env) | macOS Keychain read/write | Standard Python secret storage; macOS backend auto-selected |
| `tomli-w` | already in deps | Write config.toml from Python | Already used in existing PUT /config and PUT /config/action-item-markers |
| `shadcn Switch` | via `npx shadcn add switch` | Toggle component for all-local + feature toggles | UI-SPEC mandates it; no Switch in frontend/src/components/ui/ yet |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lucide-react` | existing | Icons: `Key`, `CheckCircle2`, `XCircle`, `Loader2` | Already in project; icons enumerated in UI-SPEC |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `httpx` (direct) | `requests` (also in env) | Both work; httpx preferred — already a direct dep of fastmcp, has timeout kwargs, async-compatible if needed later |
| `keyring` | subprocess `security` CLI | keyring is a proper library with error handling; security CLI is macOS-only fragile subprocess |
| Groq Python SDK | Direct httpx calls | SDK would add a new dep; httpx calls to OpenAI-compatible endpoint are ~10 lines and fully understood |

**Installation (new direct deps to add to pyproject.toml):**
```bash
uv add keyring httpx
```

**Note:** Both are already importable in the project env as transitive deps of fastmcp/httpx-sse. Adding them as direct deps makes the dependency explicit and protects against future transitive graph changes.

**Version verification:**

`httpx` confirmed 0.28.1 in project env via `uv run python -c "import httpx; print(httpx.__version__)"`.
`keyring` confirmed importable in project env (version attr absent in this build, but import succeeds).

---

## Architecture Patterns

### Recommended Project Structure

```
engine/
├── adapters/
│   ├── base.py           # unchanged
│   ├── claude_adapter.py # unchanged
│   ├── ollama_adapter.py # unchanged
│   ├── fallback_adapter.py # unchanged
│   └── groq_adapter.py   # NEW
├── router.py             # extend get_adapter() with feature param + all_local + groq toggles
└── config_loader.py      # update DEFAULT_CONFIG: llama3 defaults + groq + routing.all_local sections
```

### Pattern 1: GroqAdapter — OpenAI-compatible REST via httpx

**What:** Implements `BaseAdapter.generate()` by POSTing to `https://api.groq.com/openai/v1/chat/completions`. API key retrieved from Keychain at call time (not cached).

**When to use:** When `router.get_adapter()` selects Groq for a feature group.

```python
# Source: Groq API docs (https://console.groq.com/docs/text-chat) + claude_adapter.py pattern
import httpx
import keyring
from engine.adapters.base import BaseAdapter

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

class GroqAdapter(BaseAdapter):
    def generate(self, user_content: str, system_prompt: str = "") -> str:
        api_key = keyring.get_password("second-brain", "groq_api_key")
        if not api_key:
            raise RuntimeError("GroqAdapter: no API key in Keychain")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})
        resp = httpx.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": GROQ_MODEL, "messages": messages},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
```

### Pattern 2: router.get_adapter() — extended with feature param

**What:** `get_adapter()` gains an optional `feature: str = "public"` parameter. Routing precedence:
1. `all_local=true` → return OllamaAdapter for pii_model (same as current pii routing)
2. `groq.[feature]=true` AND `keyring.get_password(...)` is not None → return `FallbackAdapter(GroqAdapter(), ClaudeAdapter())`
3. Existing behaviour (sensitivity → model key lookup)

**Critical:** `feature` param must be passed from ALL call sites that want Groq routing. Call sites: `ask_brain()` in `intelligence.py`, and any future digest/person_synthesis callers. Call sites that don't pass `feature` get existing behaviour (no Groq).

```python
# Extend router.py — pseudocode showing the new logic
def get_adapter(sensitivity: str, config_path: Path, feature: str = "") -> BaseAdapter:
    config = load_config(config_path)
    routing = config.get("routing", {})

    # Rule 1: all_local overrides everything
    if routing.get("all_local", False):
        return _build_ollama(config)  # use pii_model (llama3)

    # Rule 2: Groq feature toggle
    if feature and config.get("groq", {}).get(feature, False):
        import keyring as _kr
        if _kr.get_password("second-brain", "groq_api_key"):
            from engine.adapters.groq_adapter import GroqAdapter
            from engine.adapters.claude_adapter import ClaudeAdapter
            from engine.adapters.fallback_adapter import FallbackAdapter
            return FallbackAdapter(GroqAdapter(), ClaudeAdapter())

    # Rule 3: existing sensitivity-based routing (unchanged)
    ...
```

### Pattern 3: Flask Keychain endpoints — follow action-item-markers pattern

**What:** Three new endpoints in `api.py`. Pattern: `GET /config/groq` reads from Keychain (never returns value), `POST /config/groq` writes, `DELETE /config/groq` removes.

**Reference:** `engine/api.py` lines 1171–1200 (action-item-markers GET/PUT). Key difference: these write to Keychain, not config.toml.

```python
# Source: engine/api.py existing pattern + keyring docs
@app.get("/config/groq")
def get_groq_config():
    import keyring as _kr
    key = _kr.get_password("second-brain", "groq_api_key")
    return jsonify({"configured": key is not None})

@app.post("/config/groq")
def save_groq_key():
    import keyring as _kr
    data = request.get_json(force=True, silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key.startswith("gsk_"):
        return jsonify({"error": "Key format invalid — Groq keys start with gsk_"}), 400
    _kr.set_password("second-brain", "groq_api_key", api_key)
    return jsonify({"ok": True})

@app.delete("/config/groq")
def delete_groq_key():
    import keyring as _kr
    try:
        _kr.delete_password("second-brain", "groq_api_key")
    except _kr.errors.PasswordDeleteError:
        pass  # already absent — idempotent
    return jsonify({"ok": True})

@app.post("/config/groq/test")
def test_groq_connection():
    import keyring as _kr
    import httpx
    key = _kr.get_password("second-brain", "groq_api_key")
    if not key:
        return jsonify({"ok": False, "error": "No key configured"})
    try:
        resp = httpx.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return jsonify({"ok": True, "error": None})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})
```

### Pattern 4: Signalling fallback provider to Flask layer

**Problem:** `FallbackAdapter.generate()` returns a string; the caller (`ask_brain()`) cannot detect which adapter was used.

**Solution:** Wrap the `ask_brain()` call site in `intelligence.py` to catch a known exception or use a wrapper class. Simplest approach: subclass `FallbackAdapter` as `TrackedFallbackAdapter` that sets an instance attribute `used_fallback: bool` after `generate()` completes, OR check adapter type in the result path.

**Recommended approach (Claude's discretion):** Add a `used_fallback: bool = False` attribute to `FallbackAdapter` itself (non-breaking addition). Set to `True` in the `except` branch. The Flask endpoint checks `adapter.used_fallback` after `generate()` returns.

```python
# FallbackAdapter modification (non-breaking)
class FallbackAdapter(BaseAdapter):
    def __init__(self, primary, fallback):
        self._primary = primary
        self._fallback = fallback
        self.used_fallback = False  # NEW attribute

    def generate(self, user_content, system_prompt=""):
        try:
            result = self._primary.generate(user_content, system_prompt)
            self.used_fallback = False
            return result
        except Exception as exc:
            logger.warning(...)
            self.used_fallback = True  # NEW
            return self._fallback.generate(user_content, system_prompt)
```

### Pattern 5: config.toml new sections

```toml
# New entries in DEFAULT_CONFIG / user's config.toml
[routing]
all_local = false          # NEW: overrides everything to Ollama when true
# existing keys unchanged...

[groq]
ask_brain = false          # NEW: per-feature routing toggles
followup_questions = false
digest = false
person_synthesis = false
```

### Anti-Patterns to Avoid

- **Caching the Groq API key in memory:** Violates D-02. Always retrieve from Keychain at call time. Keychain read is fast (~1ms on macOS) and allows runtime key rotation.
- **Storing `all_local` or Groq toggles in the same PUT /config endpoint without updating `allowed_routing_keys`:** The existing `put_config()` has an allowlist. The new all_local toggle should either be added to the allowlist or handled in a separate `PUT /config/routing-extended` — recommend adding to the same endpoint via a new `allowed_routing_extended_keys` check.
- **Calling `keyring.delete_password()` without catching `PasswordDeleteError`:** Raises if key doesn't exist. Always wrap in try/except for idempotent behaviour.
- **Hardcoding `llama3.2` in tests:** `test_router.py` writes TOML bytes with `llama3.2` hardcoded. After changing DEFAULT_CONFIG, any test using `tmp_config_toml` (conftest fixture) that relies on DEFAULT_CONFIG will pick up `llama3` — check conftest to see if the fixture writes hardcoded TOML or uses DEFAULT_CONFIG.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| macOS Keychain storage | Custom subprocess calls to `security` CLI | `keyring` library | Handles all macOS backends, error cases, token expiry, keychain prompts |
| Groq HTTP client | Requests + manual retry logic | `httpx` with `raise_for_status()` | Built-in connection pooling, timeout handling, proper error hierarchy |
| OpenAI-compatible parsing | Manual JSON path extraction | Standard `resp.json()["choices"][0]["message"]["content"]` | Groq is fully OpenAI-compatible; same path as every OpenAI client |
| Config defaults merging | Manual dict merge | Deep merge: `DEFAULT_CONFIG` as base, `tomllib.load()` result overlaid | `load_config()` already returns full toml — any missing key falls back to DEFAULT_CONFIG in Python callers |

**Key insight:** The Groq API is entirely OpenAI-compatible. The GroqAdapter is ~25 lines with no custom parsing logic needed beyond standard JSON path access.

---

## Common Pitfalls

### Pitfall 1: `load_config()` does not merge with DEFAULT_CONFIG

**What goes wrong:** `load_config()` returns ONLY what's in the user's `config.toml`. If the user's config.toml exists but lacks the new `[groq]` section, `config.get("groq", {})` returns `{}` and toggles default to `False` — which is correct behaviour. BUT the router must always use `.get("groq", {}).get("ask_brain", False)` not direct access, or a KeyError results.

**Why it happens:** `load_config()` returns raw tomllib output, not merged with DEFAULT_CONFIG. `DEFAULT_CONFIG` is only returned if the file is absent.

**How to avoid:** Always use `.get()` with defaults for any new config key. The planner must note this in every task touching config reads.

### Pitfall 2: `put_config()` allowlist silently drops new keys

**What goes wrong:** The existing `PUT /config` endpoint has `allowed_routing_keys = {"public_model", "private_model", "pii_model", "fallback_model"}`. If the all-local toggle is saved via the global Save button through the same endpoint without updating the allowlist, the write is silently dropped.

**Why it happens:** Defensive allowlist in `put_config()` at `api.py:1149`.

**How to avoid:** Either (a) add `"all_local"` to the `allowed_routing_keys` set, or (b) handle `[routing].all_local` and `[groq].*` in a dedicated `PUT /config/groq-settings` endpoint. Option (b) is cleaner and avoids widening the existing allowlist.

**Recommendation:** New endpoint `PUT /config/groq-settings` that handles `routing.all_local` + `groq.*` toggles. The existing global Save button in SettingsModal should call both `PUT /config` (existing) and `PUT /config/groq-settings` (new) on save.

### Pitfall 3: `ask_brain()` calls `_router.get_adapter(sensitivity, CONFIG_PATH)` without a feature param

**What goes wrong:** The existing `_call_adapter()` inner function in `ask_brain()` calls `get_adapter(sensitivity, CONFIG_PATH)` — no feature param. Adding `feature` as a new optional param to `get_adapter()` is backward-compatible, but the call site in `intelligence.py` must be updated to pass `feature="ask_brain"` for the public sensitivity path.

**Why it happens:** `ask_brain()` uses a generic sensitivity string; the feature identity is not currently passed.

**How to avoid:** The plan must explicitly update `intelligence.py ask_brain()` to pass `feature="ask_brain"` to `get_adapter()` for the public content path.

### Pitfall 4: `FallbackAdapter` used_fallback is shared state on instance

**What goes wrong:** If the `ask_brain()` function is called concurrently (multiple Flask requests), the same `FallbackAdapter` instance may have `used_fallback` overwritten by a concurrent request. This is only a problem if adapters are module-level singletons.

**Why it happens:** Potential module-level caching. However, current `get_adapter()` creates a new adapter instance on every call (no caching), so each request gets its own `FallbackAdapter` instance. This is safe.

**How to avoid:** Verify `get_adapter()` creates fresh instances. It does — `_build_adapter()` calls `adapter_cls(...)` each time. Safe as-is.

### Pitfall 5: shadcn Switch component not installed

**What goes wrong:** SettingsModal references `Switch` from `@/components/ui/switch` but that file does not exist. Build fails.

**Why it happens:** Switch is not yet in `frontend/src/components/ui/` — confirmed by UI-SPEC: "New component required: Switch from shadcn official registry."

**How to avoid:** First task in UI plan must install Switch: `npx shadcn add switch` run from `frontend/` directory.

### Pitfall 6: `llama3` vs `llama3.2` model name change breaks existing tests

**What goes wrong:** `test_router.py:test_config_change_no_restart` writes TOML bytes hardcoding `llama3.2`. After DEFAULT_CONFIG changes, test data still passes `llama3.2`. This is fine for that test. BUT `test_config_loader.py` or `test_adapters.py` fixture `tmp_config_toml` may use DEFAULT_CONFIG — after change to `llama3`, model name `ollama/llama3.2` is gone from DEFAULT_CONFIG models dict, potentially causing `KeyError` in tests that reference it.

**How to avoid:** Check `conftest.py` tmp_config_toml fixture — if it writes hardcoded TOML, it's isolated. If it uses DEFAULT_CONFIG, update fixture or add `llama3` model entry alongside `llama3.2` in DEFAULT_CONFIG during transition.

---

## Code Examples

Verified patterns from official sources:

### Groq chat completions (httpx, no SDK)

```python
# Source: https://console.groq.com/docs/text-chat (OpenAI-compatible endpoint)
import httpx

resp = httpx.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    },
    timeout=30.0,
)
resp.raise_for_status()
answer = resp.json()["choices"][0]["message"]["content"]
```

### keyring macOS Keychain

```python
# Source: https://pypi.org/project/keyring/ — standard usage
import keyring

# Store
keyring.set_password("second-brain", "groq_api_key", "gsk_...")

# Retrieve (returns None if absent)
key = keyring.get_password("second-brain", "groq_api_key")

# Delete
try:
    keyring.delete_password("second-brain", "groq_api_key")
except keyring.errors.PasswordDeleteError:
    pass  # already gone — idempotent
```

### Groq models endpoint for connectivity test

```python
# Source: https://console.groq.com/docs/api-reference (GET /openai/v1/models)
import httpx
resp = httpx.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {key}"},
    timeout=10.0,
)
resp.raise_for_status()  # raises on 401 (invalid key), 429 (rate limit), etc.
```

### shadcn Switch (React)

```tsx
// Source: shadcn official registry — installed via npx shadcn add switch
import { Switch } from "@/components/ui/switch"

<div className="flex items-center justify-between py-2">
  <div>
    <p className="text-xs font-medium">All-local mode</p>
    <p className="text-xs text-muted-foreground">Use local Ollama for everything — full privacy mode</p>
  </div>
  <Switch checked={allLocal} onCheckedChange={setAllLocal} />
</div>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `llama3.2` (3B) as default local model | `llama3` (8B) | Phase 44 | Better quality for ask_brain, digest, person synthesis |
| Claude subprocess only for public queries | Groq (cloud, fast) or Claude subprocess (fallback) | Phase 44 | 30–90s → < 20s for ask_brain |
| No Keychain integration | macOS Keychain via `keyring` | Phase 44 | API key never touches disk |

**Deprecated/outdated:**
- `ollama/llama3.2` model key in DEFAULT_CONFIG: replaced by `ollama/llama3`. Old key continues working in existing user config.toml until user saves via Settings.

---

## Open Questions

1. **`ask_brain()` PII path with Groq routing**
   - What we know: D-06 says PII always stays local regardless. `ask_brain()` already splits results into `public_items` and `pii_items` and routes separately.
   - What's unclear: When Groq is enabled for `ask_brain`, does the PII-sensitivity path still use Ollama? Yes — the existing `tasks` loop in `ask_brain()` calls `get_adapter(sensitivity, ...)` per task. PII sensitivity → `routing.pii_model` → Ollama, unchanged. Only the `public` sensitivity path benefits from Groq. The planner must ensure the feature param is only passed for the public path.

2. **`followup_questions`, `digest`, `person_synthesis` call sites**
   - What we know: These features are in the Groq toggle list but the CONTEXT.md only explicitly addresses `ask_brain` wiring.
   - What's unclear: Where exactly in `intelligence.py` or `api.py` do digest/person_synthesis/followup_questions call `get_adapter()`? The planner should check each call site.
   - Recommendation: Scope the initial implementation to `ask_brain` feature routing (highest value). The other three toggles can write to config but their `feature` param wiring is a "best effort" in this phase — the toggles are visible in UI but only activate when the matching call site passes the feature param.

3. **Global Save button scope**
   - What we know: The existing Save button in SettingsModal calls `PUT /config` which has an allowlist. The new `all_local` and `[groq].*` keys are not in that allowlist.
   - Recommendation: Plan must explicitly add a new `PUT /config/groq-settings` endpoint and wire the frontend global Save to call it alongside the existing `PUT /config`.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `httpx` | GroqAdapter HTTP calls | ✓ | 0.28.1 (transitive) | — |
| `keyring` | Keychain read/write | ✓ | 25.7.0 (transitive, importable) | — |
| `tomli-w` | config.toml writes | ✓ | already direct dep | — |
| `npx` / Node | shadcn Switch install | ✓ | host only | — |
| Groq API internet access | GroqAdapter + test endpoint | ✓ (assumed) | — | Fall back to ClaudeAdapter |
| `llama3` (8B) Ollama model | DEFAULT_CONFIG change | ✓ (stated in phase desc: "already installed") | — | Keep llama3.2 if not installed |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** Groq internet access — FallbackAdapter to ClaudeAdapter handles outages. `llama3` Ollama model — stated as already installed by user; if absent at runtime, OllamaAdapter raises, which is acceptable (model name visible in Settings).

**Dep additions required:** `keyring` and `httpx` must be added to `pyproject.toml` direct deps even though they're currently transitive. Run `uv add keyring httpx` before implementing GroqAdapter.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7+ |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_adapters.py tests/test_router.py tests/test_api.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | GroqAdapter.generate() calls Groq endpoint with correct headers | unit | `uv run pytest tests/test_adapters.py -k groq -x` | ❌ Wave 0 |
| D-02 | GroqAdapter retrieves key from Keychain at call time, never caches | unit | `uv run pytest tests/test_adapters.py -k groq_keychain -x` | ❌ Wave 0 |
| D-04/D-05 | router all_local=true returns OllamaAdapter regardless of Groq toggle | unit | `uv run pytest tests/test_router.py -k all_local -x` | ❌ Wave 0 |
| D-05 | router with groq toggle + key returns FallbackAdapter(Groq, Claude) | unit | `uv run pytest tests/test_router.py -k groq_feature -x` | ❌ Wave 0 |
| D-05 | router without groq toggle returns existing behaviour (unchanged) | unit | `uv run pytest tests/test_router.py -x -q` | ✅ existing |
| D-07 | DEFAULT_CONFIG uses llama3 not llama3.2 | unit | `uv run pytest tests/test_config_loader.py -x -q` | ✅ existing (verify passes after change) |
| D-08 | GET /config/groq returns {configured: false} when no key | unit | `uv run pytest tests/test_api.py -k groq_config -x` | ❌ Wave 0 |
| D-08 | POST /config/groq saves key to Keychain | unit | `uv run pytest tests/test_api.py -k save_groq_key -x` | ❌ Wave 0 |
| D-08 | DELETE /config/groq removes key | unit | `uv run pytest tests/test_api.py -k delete_groq_key -x` | ❌ Wave 0 |
| D-09 | POST /config/groq/test returns {ok: true} for valid key | unit (mock httpx) | `uv run pytest tests/test_api.py -k test_groq_connection -x` | ❌ Wave 0 |
| D-11 | GroqAdapter failure falls back to ClaudeAdapter | unit | `uv run pytest tests/test_adapters.py -k groq_fallback -x` | ❌ Wave 0 |
| D-12 | ask_brain endpoint returns provider=fallback when fallback activates | unit | `uv run pytest tests/test_api.py -k ask_brain_provider -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_adapters.py tests/test_router.py -x -q`
- **Per wave merge:** `uv run pytest tests/test_adapters.py tests/test_router.py tests/test_api.py tests/test_config_loader.py -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_adapters.py` — add GroqAdapter tests (file exists, append to it)
- [ ] `tests/test_router.py` — add all_local and groq feature routing tests (file exists, append)
- [ ] `tests/test_api.py` — add Keychain endpoint tests with mocked `keyring` (file exists, append)
- `conftest.py` shared fixtures: `mock_keyring` fixture needed (patch `keyring.get_password`, `keyring.set_password`, `keyring.delete_password`)

*(All target test files already exist — no new files needed, append new test functions)*

---

## Sources

### Primary (HIGH confidence)

- Groq API docs: https://console.groq.com/docs/text-chat — chat completions endpoint, message format
- Groq API docs: https://console.groq.com/docs/api-reference — models endpoint URL confirmed
- keyring PyPI: https://pypi.org/project/keyring/ — set_password/get_password/delete_password API
- Project source: `engine/adapters/` — BaseAdapter interface, ClaudeAdapter, OllamaAdapter patterns
- Project source: `engine/router.py` — full get_adapter() implementation
- Project source: `engine/api.py` lines 1128–1200 — GET/PUT /config and /config/action-item-markers patterns
- Project source: `engine/config_loader.py` — DEFAULT_CONFIG structure, load_config() semantics
- Project source: `engine/adapters/fallback_adapter.py` — FallbackAdapter.generate() exact implementation
- Project source: `tests/test_adapters.py`, `tests/test_router.py` — existing test patterns
- Project source: `frontend/src/components/SettingsModal.tsx` — existing UI state patterns
- UI-SPEC: `.planning/phases/44-.../44-UI-SPEC.md` — complete interaction contract for Settings section
- `pyproject.toml` + `uv.lock` — confirmed httpx 0.28.1 and keyring 25.7.0 in project env

### Secondary (MEDIUM confidence)

- WebSearch → Groq API: confirmed OpenAI-compatible endpoint `https://api.groq.com/openai/v1/chat/completions`, GET /models for connectivity test
- WebSearch → keyring macOS: confirmed set_password/get_password/delete_password standard API, macOS 11+ support

### Tertiary (LOW confidence)

- None

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all deps verified in project env, Groq API confirmed via official docs
- Architecture: HIGH — existing adapter/router patterns fully read, new patterns are straightforward extensions
- Pitfalls: HIGH — derived from direct source code reading, not speculation
- UI: HIGH — UI-SPEC already written and approved, shadcn Switch confirmed as only new component

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable API surface; Groq model availability should be re-checked if > 30 days)
