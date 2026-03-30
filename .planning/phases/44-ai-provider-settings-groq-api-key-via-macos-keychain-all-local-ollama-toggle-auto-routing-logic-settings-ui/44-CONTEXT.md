# Phase 44: AI Provider Settings — Context

**Gathered:** 2026-03-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Add Groq as an AI provider option (API key stored in macOS Keychain via `keyring`), add an all-local Ollama toggle for full privacy mode, wire auto-routing logic that honours these settings per feature group, and expose both controls in Settings UI. Switch default local model from `llama3.2` (3B) to `llama3` (8B). Performance goal: Ask Brain < 20s.

**In scope:**
- New `engine/adapters/groq_adapter.py` (Groq API via HTTP)
- Keychain integration: `keyring.set_password("second-brain", "groq_api_key", value)` — new Flask endpoints: `GET /config/groq` → `{configured: bool}`, `POST /config/groq` (save key), `DELETE /config/groq` (remove key)
- Connectivity test endpoint: `POST /config/groq/test` — lightweight Groq ping, returns `{ok: bool, error?: str}`
- Per-feature-group Groq routing toggles stored in `config.toml [groq]`; feature groups: `ask_brain`, `followup_questions`, `digest`, `person_synthesis`
- All-local toggle: `config.toml [routing] all_local = true/false` — when `true`, overrides ALL routing (even Groq-enabled features) to local Ollama
- Updated `engine/router.py` `get_adapter()` to check all-local flag first, then Groq toggles, then existing routing keys
- `DEFAULT_CONFIG` in `config_loader.py`: switch `pii_model` and `fallback_model` from `ollama/llama3.2` → `ollama/llama3`; add `groq/llama-3.3-70b-versatile` model entry
- Settings UI: Groq API key section (enter → save → `✓ Configured + Remove button`), connectivity test indicator, all-local toggle, per-feature Groq toggles
- Failure handling: Groq failure → fall back to claude subprocess (reuse `FallbackAdapter`), show subtle warning toast in UI

**Out of scope:**
- Groq for MCP tool calls — only the GUI/`ask_brain` feature paths
- Any changes to embeddings (still Ollama nomic-embed-text)
- PII routing changes — PII always stays local regardless

</domain>

<decisions>
## Implementation Decisions

### Groq Adapter
- **D-01:** New `engine/adapters/groq_adapter.py` — calls Groq REST API directly (no SDK if avoidable; use `httpx` or `requests` already in deps). Model: `llama-3.3-70b-versatile`.
- **D-02:** API key retrieved at call time via `keyring.get_password("second-brain", "groq_api_key")`. Never stored in config.toml or on disk.
- **D-03:** `config.toml` gains a `[groq]` section with per-feature boolean toggles: `ask_brain`, `followup_questions`, `digest`, `person_synthesis`. Default: all `false` (Groq opt-in, not default).

### All-Local Toggle
- **D-04:** `config.toml [routing] all_local = false` (default). When `true`, `router.get_adapter()` always returns the Ollama adapter regardless of Groq key or feature toggles.
- **D-05:** Routing precedence (in order):
  1. `all_local = true` → Ollama for everything
  2. `groq.[feature] = true` AND Groq key present → Groq for that feature (fallback: claude subprocess)
  3. Existing `routing.*_model` config keys (current behaviour unchanged)
- **D-06:** PII-flagged content is ALWAYS local (existing rule, unchanged). All-local toggle adds no new behaviour for PII — it's redundant but that's fine.

### Default Local Model Change
- **D-07:** Switch `pii_model`, `fallback_model`, and the `ollama/llama3.2` model entry in `DEFAULT_CONFIG` to use `llama3` (8B). Update `config_loader.py`. Existing `config.toml` files with `llama3.2` continue working until user saves via Settings (at which point new defaults apply).

### Keychain & Flask Endpoints
- **D-08:** Three new Flask endpoints:
  - `GET /config/groq` → `{"configured": true|false}` (never returns the key value)
  - `POST /config/groq` body `{"api_key": "gsk_..."}` → saves to Keychain, returns `{"ok": true}`  # pragma: allowlist secret
  - `DELETE /config/groq` → removes from Keychain, returns `{"ok": true}`
- **D-09:** New `POST /config/groq/test` → reads key from Keychain, makes minimal Groq API call (e.g. list models or zero-token completion), returns `{"ok": bool, "error": str | null}`. Called from Settings UI immediately after saving a key.

### Settings UI
- **D-10:** New "AI Provider" section in SettingsModal (above or below existing "AI model routing"). Contains:
  - **Groq API key:** password input (empty on load) + Save button → on success shows `✓ Configured` text + `Remove` button + connectivity test result (`✓ Connected` / `✗ Invalid key`). Remove → returns to empty input state.
  - **All-local toggle:** `<Switch>` component, labelled "Use all-local Ollama (full privacy mode)". When ON, disables Groq feature toggles visually.
  - **Groq feature toggles:** four `<Switch>` toggles for ask_brain / followup_questions / digest / person_synthesis. Greyed out when all-local is ON.

### Failure Handling
- **D-11:** Groq runtime failure (network error, rate limit, expired key) → `FallbackAdapter(GroqAdapter, ClaudeAdapter)` — existing pattern in `router.py`. No new code needed beyond wiring.
- **D-12:** When fallback activates, the `ask_brain` Flask endpoint returns a response with `{"answer": "...", "sources": [...], "provider": "fallback"}`. Frontend shows a subtle toast: "Groq unavailable, used fallback model."

### Claude's Discretion
- Exact Tailwind classes for the new Settings section (follow existing section style)
- Whether `groq_adapter.py` uses `httpx` (already dep?) or `requests` — pick whichever is in `pyproject.toml`
- Whether connectivity test endpoint is called automatically on save or requires a separate "Test" button click (recommended: auto on save)
- Whether `FallbackAdapter` needs a callback/flag to signal fallback was used, or whether the endpoint detects it via exception/flag after the call

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Routing architecture (primary)
- `engine/router.py` — `get_adapter()` function; `ADAPTER_MAP`; `_build_adapter()` — extend all three for Groq
- `engine/config_loader.py` — `DEFAULT_CONFIG` structure; `load_config()` — update defaults here
- `engine/adapters/base.py` — `BaseAdapter` interface; new `GroqAdapter` must implement it
- `engine/adapters/claude_adapter.py` — reference implementation
- `engine/adapters/ollama_adapter.py` — reference implementation
- `engine/adapters/fallback_adapter.py` — reuse for Groq→Claude fallback wiring

### Flask API patterns
- `engine/api.py` lines ~1130–1165 — existing `GET /config` and `POST /config` endpoints; follow same pattern for Groq endpoints
- `engine/api.py` lines ~1082–1162 — action-item markers endpoints (`GET/POST /config/action-item-markers`) — closest existing example of "write a config sub-section"

### Settings UI patterns
- `frontend/src/components/SettingsModal.tsx` — existing sections (AI routing dropdowns, ollama host, markers); new Groq section fits here
- `frontend/src/components/ui/` — `Switch` component (if exists), `Button`, `Input` — use existing

### Ask Brain path
- `engine/intelligence.py` line ~1082 — `ask_brain()` function; `router.get_adapter("public", CONFIG_PATH)` call site
- `engine/api.py` lines ~2117–2130 — `ask_brain_endpoint()` Flask route; add `provider` field to response for fallback toast

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FallbackAdapter` in `engine/adapters/fallback_adapter.py` — existing primary→fallback pattern; wire `GroqAdapter(primary)` + `ClaudeAdapter(fallback)` directly
- `load_config()` in `config_loader.py` — reads fresh every call; Groq feature toggles live here
- `get_adapter()` in `router.py` — extend sensitivity→model→adapter dispatch to check all_local and groq toggles

### Established Patterns
- Config pattern: new settings go in `config.toml` under a `[section]` key; `DEFAULT_CONFIG` provides the fallback
- Adapter pattern: implement `BaseAdapter.generate(user_content, system_prompt) -> str`
- Flask endpoint pattern: `GET /config/X` returns config subset; `POST /config/X` writes back via `load_config` → mutate → `tomllib` write (check how existing writes work)
- Settings UI pattern: `useState` for each section, `useEffect` to load on open, save via `fetch POST`

### Integration Points
- `engine/router.py` `get_adapter()` → add all_local check + groq feature toggle dispatch (feature group passed as new param or derived from sensitivity + caller context)
- `engine/intelligence.py` `ask_brain()` → pass feature group identifier to `get_adapter()` (or use a dedicated `get_ask_brain_adapter()` wrapper)
- `engine/api.py` `ask_brain_endpoint()` → add `provider` field to response JSON
- `frontend/src/components/SettingsModal.tsx` → new "AI Provider" section component block
- `frontend/src/components/AskBrainModal.tsx` → read `provider` from response, show fallback toast if `provider === "fallback"`

</code_context>

<specifics>
## Specific Ideas

- Groq model: `llama-3.3-70b-versatile` (from roadmap)
- Keychain service name: `"second-brain"`, key name: `"groq_api_key"` (from roadmap design session)
- Performance goal: Ask Brain < 20s end-to-end (Groq should hit this easily vs claude subprocess which can be 30–90s)
- All-local toggle in Settings: label "Use all-local Ollama (full privacy mode)" — makes the privacy intent explicit to the user

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 44-ai-provider-settings-groq-api-key-via-macos-keychain-all-local-ollama-toggle-auto-routing-logic-settings-ui*
*Context gathered: 2026-03-30*
