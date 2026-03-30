---
phase: 44-ai-provider-settings
plan: "01"
subsystem: ai-adapter-routing
tags: [groq, adapter, router, keychain, config, tdd]
dependency_graph:
  requires: []
  provides: [GroqAdapter, router-all_local, router-groq-feature, DEFAULT_CONFIG-groq]
  affects: [engine/router.py, engine/config_loader.py, engine/adapters/fallback_adapter.py]
tech_stack:
  added: [keyring>=25.0, httpx>=0.27]
  patterns: [adapter-pattern, tdd-red-green, three-tier-routing-precedence]
key_files:
  created:
    - engine/adapters/groq_adapter.py
  modified:
    - engine/adapters/fallback_adapter.py
    - engine/config_loader.py
    - engine/router.py
    - pyproject.toml
    - tests/test_adapters.py
    - tests/test_router.py
    - tests/conftest.py
decisions:
  - "Keep both ollama/llama3 and ollama/llama3.2 in DEFAULT_CONFIG models dict for backward compat (Pitfall 6 from RESEARCH.md)"
  - "Test assertions for no-Groq paths check FallbackAdapter._primary is not GroqAdapter (not isinstance ClaudeAdapter) — existing fallback_model wraps claude in FallbackAdapter"
  - "PII sensitivity skips Rule 2 at router level (sensitivity != 'pii' guard) rather than in call sites"
metrics:
  duration_seconds: 338
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_modified: 7
---

# Phase 44 Plan 01: Groq Adapter + Router Extensions Summary

GroqAdapter (httpx + macOS Keychain) with three-tier routing precedence: all_local > groq-feature > existing sensitivity routing, plus FallbackAdapter.used_fallback tracking.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 (RED) | Failing tests for GroqAdapter, FallbackAdapter.used_fallback, DefaultConfig | 645e43e | tests/test_adapters.py |
| 1 (RED) | Failing tests for router all_local + groq feature | d8f4795 | tests/test_router.py |
| 1 (GREEN) | GroqAdapter + FallbackAdapter.used_fallback + DEFAULT_CONFIG | 57037b3 | engine/adapters/groq_adapter.py, fallback_adapter.py, config_loader.py, pyproject.toml, tests/conftest.py |
| 2 (GREEN) | Router all_local + groq feature dispatch | 37c52df | engine/router.py, tests/test_router.py |

## What Was Built

**GroqAdapter** (`engine/adapters/groq_adapter.py`): Calls `https://api.groq.com/openai/v1/chat/completions` via httpx. Retrieves API key from macOS Keychain at call time (`keyring.get_password("second-brain", "groq_api_key")`). Raises RuntimeError if no key. Uses `llama-3.3-70b-versatile`.

**FallbackAdapter.used_fallback**: Non-breaking attribute addition. Set to `False` in `__init__` and on primary success; set to `True` in the `except` branch before calling fallback. Enables Flask endpoints to detect which provider was used.

**DEFAULT_CONFIG updates**: `pii_model` and `fallback_model` changed from `ollama/llama3.2` to `ollama/llama3`. New `routing.all_local = False` and `groq` section with four feature toggles all defaulting to `False`. Both `ollama/llama3` and `ollama/llama3.2` kept in models dict for backward compat.

**Router extensions**: `get_adapter()` gains optional `feature: str = ""` parameter. Three-tier precedence:
1. `routing.all_local=true` → OllamaAdapter (overrides everything)
2. `groq.[feature]=true` AND Keychain key present → `FallbackAdapter(GroqAdapter, ClaudeAdapter)` (skipped for PII sensitivity)
3. Existing sensitivity-based routing (unchanged)

## Test Results

41 tests passing across `test_adapters.py`, `test_router.py`, `test_config_loader.py`. No regressions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion fixes for no-Groq fallthrough paths**

- **Found during:** Task 2 GREEN phase
- **Issue:** Tests `test_groq_feature_enabled_but_no_key_falls_through`, `test_groq_feature_disabled_returns_existing_routing`, and `test_no_feature_param_returns_existing_routing` asserted `isinstance(adapter, ClaudeAdapter)`. However, the test config has `fallback_model = "ollama/llama3"` (different from `public_model = "claude"`), so Rule 3 correctly creates `FallbackAdapter(claude, ollama)` — not a bare `ClaudeAdapter`.
- **Fix:** Changed assertions to check `adapter._primary is not GroqAdapter` when adapter is a FallbackAdapter — correctly verifying no Groq is in the chain rather than checking the wrapper type.
- **Files modified:** `tests/test_router.py`

## Known Stubs

None — all new code is fully wired and tested.

## Self-Check: PASSED

- engine/adapters/groq_adapter.py: FOUND
- engine/adapters/fallback_adapter.py: FOUND (used_fallback in __init__ and except branch)
- engine/config_loader.py: FOUND (groq section, all_local, llama3)
- engine/router.py: FOUND (feature param, all_local check, groq check)
- pyproject.toml: FOUND (keyring>=25.0, httpx>=0.27)
- Commits 645e43e, d8f4795, 57037b3, 37c52df: all present in git log
