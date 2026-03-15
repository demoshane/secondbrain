---
phase: 17-api-layer-and-setup-automation
plan: "00"
subsystem: testing
tags: [tdd, api, setup-automation, red-scaffold]
dependency_graph:
  requires: []
  provides:
    - tests/test_api.py (RED scaffold — 9 stubs for API layer)
    - tests/test_init_brain.py (extended — 9 new stubs for Drive/Ollama)
    - pyproject.toml (flask, waitress, flask-cors deps + sb-api entry point)
  affects:
    - 17-01 (must pass all test_api.py tests GREEN)
    - 17-02 (must pass all new test_init_brain.py stubs GREEN)
tech_stack:
  added:
    - flask>=3.0
    - waitress>=3.0
    - flask-cors>=4.0
  patterns:
    - TDD RED scaffold — ImportError at collection level confirms unimplemented modules
    - Flask test client pattern with @pytest.fixture client
key_files:
  created:
    - tests/test_api.py
  modified:
    - tests/test_init_brain.py
    - pyproject.toml
decisions:
  - "Import new symbols at module level (not inside tests) — collection-level ImportError is sufficient RED signal"
  - "sb-api entry point added to pyproject.toml alongside other sb-* CLI commands"
metrics:
  duration: 85s
  completed: "2026-03-15"
  tasks_completed: 2
  files_modified: 3
---

# Phase 17 Plan 00: API Layer and Setup Automation RED Scaffold Summary

**One-liner:** RED scaffold with 9 API stubs (Flask test client) and 9 Drive/Ollama stubs, plus flask/waitress/flask-cors deps added to pyproject.toml.

## What Was Built

Wave 0 TDD scaffold for Phase 17. Created `tests/test_api.py` with 9 failing stubs covering all API behaviors (health, notes list, search, read, actions). Extended `tests/test_init_brain.py` with 4 new test classes (9 stubs) covering Drive detection (macOS/Windows), Drive exit-on-missing, Ollama binary ensure, and Ollama model size warning. Added Flask, Waitress, and flask-cors to `pyproject.toml` dependencies and the `sb-api` entry point.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Flask deps and create tests/test_api.py scaffold | 6cf6a29 | pyproject.toml, tests/test_api.py |
| 2 | Extend tests/test_init_brain.py with Drive and Ollama stubs | 8e56e38 | tests/test_init_brain.py |

## Verification

Both test files fail at collection with ImportError — RED state confirmed:
- `tests/test_api.py`: `ImportError: cannot import name 'app' from 'engine.api'` (module doesn't exist)
- `tests/test_init_brain.py`: `ImportError: cannot import name 'detect_drive_macos' from 'engine.init_brain'` (symbols don't exist)

Flask, waitress, and flask-cors were installed successfully (10 packages installed via uv).

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- Import new symbols at module level rather than inside individual test methods — collection-level ImportError is the clearest RED signal and matches the pattern established in Phase 16.
- `sb-api` entry point added to pyproject.toml alongside the existing `sb-*` CLI commands.
