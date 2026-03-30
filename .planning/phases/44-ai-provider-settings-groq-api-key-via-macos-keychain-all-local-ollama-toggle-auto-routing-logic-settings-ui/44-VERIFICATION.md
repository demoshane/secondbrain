---
phase: 44-ai-provider-settings
verified: 2026-03-30T00:00:00Z
status: human_needed
score: 18/18 must-haves verified
re_verification: false
human_verification:
  - test: "Open Settings modal and confirm AI Provider section renders with Groq key input field"
    expected: "Section heading 'AI Provider' visible, key input present, all-local toggle present"
    why_human: "Visual rendering cannot be verified without a running GUI"
  - test: "Enter a Groq API key starting with gsk_ and click Save"
    expected: "Green 'Configured' badge + 'Remove' button appear; connectivity test runs automatically and shows result"
    why_human: "Requires live Keychain interaction and API call"
  - test: "Enable all-local toggle and observe Groq feature toggles"
    expected: "Four Groq feature toggles become visually dimmed (opacity-50) and non-interactive"
    why_human: "Visual state change requires rendered UI"
  - test: "Trigger Ask Brain with Groq enabled and Groq intentionally broken (bad key)"
    expected: "Answer appears; amber toast 'Groq unavailable — used fallback model' shows for ~4 seconds"
    why_human: "Requires end-to-end flow with real Keychain and running API"
---

# Phase 44: AI Provider Settings Verification Report

**Phase Goal:** Make Ask Brain fast and snappy (<20s). Add Groq as an AI provider option — API key stored in macOS Keychain, auto-routing logic, all-local Ollama toggle, Settings UI.
**Verified:** 2026-03-30
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | GroqAdapter.generate() posts to Groq API with key from Keychain | VERIFIED | `engine/adapters/groq_adapter.py` calls `keyring.get_password("second-brain", "groq_api_key")` and `httpx.post(GROQ_API_URL, ...)` |
| 2  | Router returns OllamaAdapter when all_local=true regardless of Groq config | VERIFIED | `engine/router.py` L46-49: `if routing.get("all_local", False)` returns `OllamaAdapter` before any Groq check |
| 3  | Router returns FallbackAdapter(Groq, Claude) when groq.[feature]=true and key present | VERIFIED | `engine/router.py` L53-56: `config.get("groq", {}).get(feature, False)` + keyring check → `FallbackAdapter(GroqAdapter(), ClaudeAdapter())` |
| 4  | Router returns existing behaviour when no groq toggles or all_local | VERIFIED | Rule 3 in `engine/router.py` L59-67: unchanged sensitivity-based routing |
| 5  | DEFAULT_CONFIG uses llama3 not llama3.2 for pii_model and fallback_model | VERIFIED | `engine/config_loader.py`: `"pii_model": "ollama/llama3"`, `"fallback_model": "ollama/llama3"` |
| 6  | FallbackAdapter.used_fallback is True after primary fails | VERIFIED | `engine/adapters/fallback_adapter.py` L36: `self.used_fallback = True` in except branch |
| 7  | GET /config/groq returns configured status from Keychain | VERIFIED | `engine/api.py` L1234-1239: `@app.get("/config/groq")` calls `keyring.get_password` |
| 8  | POST /config/groq saves key to Keychain; validates gsk_ prefix | VERIFIED | `engine/api.py` L1242-1252: validates `api_key.startswith("gsk_")`, calls `keyring.set_password` |
| 9  | DELETE /config/groq removes key idempotently | VERIFIED | `engine/api.py` L1254-1262: catches `PasswordDeleteError` silently |
| 10 | POST /config/groq/test validates key against Groq API | VERIFIED | `engine/api.py` L1265-1283: calls `httpx.get("https://api.groq.com/openai/v1/models", ...)` |
| 11 | PUT /config/groq-settings persists all_local and groq toggles | VERIFIED | `engine/api.py` L1300-1323: writes to `config.toml` via `tomli_w.dump` with `allowed_groq_keys` whitelist |
| 12 | POST /ask returns provider field (groq/fallback/default) | VERIFIED | `engine/intelligence.py` L1216: `return {"answer": answer, "sources": sources, "provider": overall_provider}` |
| 13 | ask_brain() passes feature="ask_brain" for public path | VERIFIED | `engine/intelligence.py` L1165: `feature = "ask_brain" if sensitivity == "public" else ""` |
| 14 | SettingsModal shows AI Provider section | VERIFIED | `frontend/src/components/SettingsModal.tsx` L247: `<p className="text-sm font-medium mb-3">AI Provider</p>` |
| 15 | SettingsModal key management (save/remove/auto-test) | VERIFIED | `handleSaveGroqKey` (L144), `handleRemoveGroqKey` (L175), auto-test fetch L160 |
| 16 | All-local toggle disables Groq feature toggles visually | VERIFIED | L322: `<div className={allLocal ? 'opacity-50 pointer-events-none' : ''}>` |
| 17 | Groq feature toggles hidden when no key configured | VERIFIED | L319: `{groqConfigured && (` gates entire feature toggle section |
| 18 | AskBrainModal shows amber fallback toast when provider is fallback | VERIFIED | `frontend/src/components/AskBrainModal.tsx` L51-53: `if (data.provider === 'fallback') { toast.warning('Groq unavailable — used fallback model', { duration: 4000 }) }` |

**Score:** 18/18 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `engine/adapters/groq_adapter.py` | Groq REST API adapter | VERIFIED | Exports `GroqAdapter`, uses `GROQ_MODEL = "llama-3.3-70b-versatile"`, Keychain at call time |
| `engine/adapters/fallback_adapter.py` | used_fallback tracking | VERIFIED | `used_fallback: bool = False` in `__init__`, set True in except branch |
| `engine/config_loader.py` | DEFAULT_CONFIG with groq + all_local | VERIFIED | llama3 defaults, `"groq"` section with 4 boolean keys, `"all_local": False` in routing |
| `engine/router.py` | Extended get_adapter with feature + all_local | VERIFIED | `def get_adapter(sensitivity, config_path, feature="")`, three-tier precedence |
| `engine/api.py` | 6 Groq endpoints + ask provider field | VERIFIED | All 6 routes present: GET/POST/DELETE `/config/groq`, POST `/config/groq/test`, GET/PUT `/config/groq-settings` |
| `engine/intelligence.py` | ask_brain with feature wiring + provider field | VERIFIED | `_call_adapter` returns `(answer, provider)` tuple, `overall_provider` aggregation |
| `frontend/src/components/ui/switch.tsx` | shadcn Switch component | VERIFIED | Full Radix UI Switch wrapper, exports `Switch` |
| `frontend/src/components/SettingsModal.tsx` | AI Provider section | VERIFIED | All state vars, fetch calls, handlers, JSX section present |
| `frontend/src/components/AskBrainModal.tsx` | Fallback toast | VERIFIED | `data.provider` check, `toast.warning` with correct message |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `engine/router.py` | `engine/adapters/groq_adapter.py` | `from engine.adapters.groq_adapter import GroqAdapter` | WIRED | L6 module-level import; used in ADAPTER_MAP and get_adapter |
| `engine/router.py` | `engine/config_loader.py` | `config.get("groq", {})` | WIRED | L53 reads groq section from loaded config |
| `engine/api.py` | keyring | `keyring.get_password / set_password / delete_password` | WIRED | Lazy imports inside each endpoint function body; `PasswordDeleteError` caught |
| `engine/intelligence.py` | `engine/router.py` | `get_adapter(..., feature=feature)` | WIRED | L1166: `_router.get_adapter(sensitivity, CONFIG_PATH, feature=feature)` |
| `engine/api.py` | `engine/intelligence.py` | `ask_brain` returns `provider` field | WIRED | L1216 returns dict with `"provider"` key; endpoint auto-includes it via `jsonify(result)` |
| `SettingsModal.tsx` | `/config/groq` | fetch GET/POST/DELETE | WIRED | L101, L148, L177 |
| `SettingsModal.tsx` | `/config/groq-settings` | fetch GET/PUT | WIRED | L105, L206 |
| `AskBrainModal.tsx` | `/ask` | `data.provider` check | WIRED | L51: reads `data.provider` after `/ask` response |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `SettingsModal.tsx` | `groqConfigured` | `GET /config/groq` → `keyring.get_password` | Yes — live Keychain lookup | FLOWING |
| `SettingsModal.tsx` | `allLocal`, `groqToggles` | `GET /config/groq-settings` → `load_config(CONFIG_PATH)` | Yes — reads real `config.toml` | FLOWING |
| `AskBrainModal.tsx` | `data.provider` | `POST /ask` → `ask_brain()` → `_call_adapter()` → adapter detection | Yes — derives from actual adapter instance type | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED — all runnable entry points require a live Flask server (port 37491). Routes cannot be exercised without `make dev` having been run. Key behaviors are validated by the test suite instead.

---

### Requirements Coverage

D-01 through D-12 are phase-internal IDs defined in `44-CONTEXT.md` (not in `.planning/REQUIREMENTS.md`, which tracks cross-phase requirements). All 12 are accounted for:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01 | 44-01 | GroqAdapter using httpx, model llama-3.3-70b-versatile | SATISFIED | `engine/adapters/groq_adapter.py` |
| D-02 | 44-01 | API key from Keychain at call time, never on disk | SATISFIED | `keyring.get_password` called in `generate()` |
| D-03 | 44-01 | `[groq]` section in config with 4 boolean toggles, all False | SATISFIED | `config_loader.py` DEFAULT_CONFIG |
| D-04 | 44-01 | `all_local` flag in routing; when true forces Ollama | SATISFIED | `router.py` Rule 1 |
| D-05 | 44-01 | Three-tier routing precedence: all_local > groq feature > existing | SATISFIED | `router.py` L46-66 |
| D-06 | 44-01 | PII sensitivity never reaches Groq (Rule 2 skipped for pii) | SATISFIED | `router.py` L53: `sensitivity != "pii"` guard |
| D-07 | 44-01 | DEFAULT_CONFIG switches pii/fallback model to ollama/llama3 (8B) | SATISFIED | `config_loader.py` |
| D-08 | 44-02 | GET/POST/DELETE `/config/groq` Keychain endpoints | SATISFIED | `engine/api.py` L1234-1262 |
| D-09 | 44-02 | POST `/config/groq/test` connectivity test | SATISFIED | `engine/api.py` L1265-1283 |
| D-10 | 44-03 | AI Provider section in SettingsModal | SATISFIED | `SettingsModal.tsx` |
| D-11 | 44-01 | FallbackAdapter.used_fallback tracking | SATISFIED | `fallback_adapter.py` |
| D-12 | 44-02, 44-03 | provider field in /ask response; fallback toast in UI | SATISFIED | `intelligence.py` + `AskBrainModal.tsx` |

No orphaned requirements. All D-01 through D-12 are claimed by at least one plan and verified in the codebase.

---

### Anti-Patterns Found

No blockers or warnings. No TODO/FIXME/PLACEHOLDER comments in any phase 44 files. No stub patterns (empty returns, hardcoded empty arrays, console.log-only handlers) detected. The `DEFAULT_MARKERS` constant in `SettingsModal.tsx` (line 40) is a pre-existing config constant unrelated to this phase.

---

### Human Verification Required

#### 1. AI Provider Section Renders

**Test:** Open the Second Brain GUI (http://localhost:37491/ui), navigate to Settings.
**Expected:** "AI Provider" section visible with a Groq API key input field, all-local toggle, and (once key is configured) four feature toggle switches.
**Why human:** Visual rendering requires running GUI.

#### 2. Key Save + Auto-Test Flow

**Test:** Enter a valid Groq API key (starts with `gsk_`) and click Save.
**Expected:** Input clears, green "Configured" badge appears with a checkmark icon. Connectivity test runs automatically within a few seconds and shows either green "Connected" or red error text.
**Why human:** Requires live Keychain write and Groq API call.

#### 3. All-Local Toggle Disables Feature Toggles

**Test:** With a Groq key configured, enable the all-local toggle.
**Expected:** The four Groq feature toggle rows become visually dimmed and non-clickable.
**Why human:** Visual/interactive state requires rendered UI.

#### 4. Fallback Toast End-to-End

**Test:** Configure a Groq key, enable "Ask Brain" feature toggle, then invalidate the key in Keychain (or use a deliberately bad key), and submit a brain query via Ask Brain.
**Expected:** An answer appears (from fallback Claude), and an amber toast notification says "Groq unavailable — used fallback model" and fades after ~4 seconds.
**Why human:** Requires end-to-end flow with intentional Groq failure; cannot simulate Keychain state without a running service.

---

### Gaps Summary

No gaps found. All 18 observable truths are verified at code level. All 9 required artifacts exist and are substantive (not stubs). All 8 key links are wired. All 12 phase-internal requirements (D-01 through D-12) are satisfied.

Verification is gated on human sign-off for four UX flows that require a live GUI session.

---

_Verified: 2026-03-30_
_Verifier: Claude (gsd-verifier)_
