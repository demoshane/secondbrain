---
phase: 03-ai-layer
plan: "02"
subsystem: ai-routing
tags: [router, config, gdpr, dispatcher, toml]
one_liner: "Config loader with TOML fallback defaults and ModelRouter GDPR dispatcher routing by PII sensitivity"

dependency_graph:
  requires:
    - 03-01 (OllamaAdapter, ClaudeAdapter, BaseAdapter)
  provides:
    - engine/config_loader.py — load_config() + DEFAULT_CONFIG
    - engine/router.py — get_adapter() dispatcher
    - init_brain.py — config.toml creation on sb-init
  affects:
    - 03-03 (consumes get_adapter() for AI feature calls)

tech_stack:
  added:
    - tomllib (stdlib, Python 3.11+)
  patterns:
    - No-cache fresh-read pattern for hot config reload (AI-05)
    - ADAPTER_MAP dict dispatch for extensible adapter selection
    - Pathlib-only file I/O (FOUND-12)

key_files:
  created:
    - engine/config_loader.py
    - engine/router.py
  modified:
    - engine/init_brain.py

decisions:
  - load_config() has no module-level caching — every call reads from disk so config changes take effect without restart (AI-05)
  - Unknown sensitivity values fall back to public_model routing (safe default)
  - init_brain.py writes config.toml as raw string — no tomllib import needed in init path
  - config.toml creation is idempotent — does not overwrite existing user config

metrics:
  duration: "2 minutes"
  completed: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  tests_passing: 15
---

# Phase 3 Plan 02: Config Loader and ModelRouter Summary

Config loader with TOML fallback defaults and ModelRouter GDPR dispatcher routing by PII sensitivity.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Config loader with fallback defaults | 90fc1a8 | engine/config_loader.py |
| 2 | ModelRouter and sb-init config.toml creation | 9985182 | engine/router.py, engine/init_brain.py |

## What Was Built

**engine/config_loader.py** — `load_config(path)` reads a TOML config file in binary mode (required by tomllib). Returns `DEFAULT_CONFIG` dict on `FileNotFoundError` without raising. No caching at any level — every call reads disk fresh, enabling live config changes with no process restart (AI-05).

`DEFAULT_CONFIG` has:
- `routing.pii_model = "ollama/llama3.2"` — PII traffic stays local
- `routing.private_model = "claude"` and `routing.public_model = "claude"` — non-PII uses Claude

**engine/router.py** — `get_adapter(sensitivity, config_path)` is the GDPR enforcement point. Reads config fresh, resolves the model key for the given sensitivity tier (`pii`/`private`/`public`), looks up the adapter class via `ADAPTER_MAP`, and instantiates it. Unknown sensitivity values fall back to `public_model` routing. `ADAPTER_MAP = {"ollama": OllamaAdapter, "claude": ClaudeAdapter}` provides extension point for future adapters.

**engine/init_brain.py** — `sb-init` now writes a default `config.toml` to `brain/.meta/config.toml` if absent. Uses pathlib `write_text()` only (FOUND-12 compliant). Idempotent — skips write if file already exists. Reports `[CREATED]` or `[EXISTS]` status line.

## Verification

Full wave verify: 15 tests passed (tests/test_classifier.py + tests/test_adapters.py + tests/test_router.py).

Plan stated 14 tests; 15 actually collected (one additional test in test_adapters.py from 03-01).

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- engine/config_loader.py: FOUND
- engine/router.py: FOUND
- engine/init_brain.py: MODIFIED (config.toml creation added)
- Commit 90fc1a8: FOUND
- Commit 9985182: FOUND
- 15 tests passing: VERIFIED
