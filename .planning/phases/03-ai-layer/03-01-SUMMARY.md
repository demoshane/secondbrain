---
phase: 03-ai-layer
plan: "01"
subsystem: ai-layer
tags: [classifier, adapters, pii, ollama, claude, gdpr]
dependency_graph:
  requires: [03-00]
  provides: [engine/classifier.py, engine/adapters/]
  affects: [03-02, 03-03]
tech_stack:
  added: [ollama>=0.6]
  patterns: [adapter-pattern, tdd, abc-abstractmethod, subprocess-claude]
key_files:
  created:
    - engine/classifier.py
    - engine/adapters/__init__.py
    - engine/adapters/base.py
    - engine/adapters/ollama_adapter.py
    - engine/adapters/claude_adapter.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "ClaudeAdapter uses subprocess.run(['claude', '-p', ...]) — no anthropic SDK import (Max plan constraint)"
  - "OllamaAdapter default host is host.docker.internal:11434 for DevContainer compatibility"
  - "classify() frontmatter field wins over keyword scan — explicit user declaration takes priority"
  - "ClaudeAdapter passes --allowedTools '' to subprocess for AI-10 isolation"
  - "shutil.which guard in ClaudeAdapter provides clear error when claude CLI not on PATH"
metrics:
  duration: "3 minutes"
  completed: "2026-03-14"
  tasks_completed: 2
  files_changed: 7
requirements_covered: [AI-02, AI-03, AI-04, AI-06, AI-10]
---

# Phase 3 Plan 01: PII Classifier and Adapters Summary

**One-liner:** Local-only PII classifier with frozenset+regex and three adapters (BaseAdapter ABC, OllamaAdapter via ollama PyPI, ClaudeAdapter via `claude -p` subprocess) enforcing AI-10 prompt injection protection.

## What Was Built

### Task 1: PII Classifier (`engine/classifier.py`)

Pure-Python classifier with no network calls. `SENSITIVITY_VALUES` frozenset contains `{"pii", "private", "public"}`. `PII_KEYWORDS` list has 10 regex patterns compiled to `_PII_RE` at module level with `re.IGNORECASE`. `classify()` checks frontmatter field first (explicit declaration wins), then falls back to keyword scan, then defaults to `"public"`.

### Task 2: Adapter Package (`engine/adapters/`)

Four files:
- `__init__.py` — empty package marker
- `base.py` — `BaseAdapter` ABC with single abstract `generate(user_content, system_prompt="") -> str` method; docstring explicitly notes AI-10 constraint
- `ollama_adapter.py` — `OllamaAdapter(BaseAdapter)` using `ollama.Client(host=host)`; builds messages list with optional system role followed by user role; returns `response.message.content`
- `claude_adapter.py` — `ClaudeAdapter(BaseAdapter)` using `subprocess.run(["claude", "-p", ...], --allowedTools "")`;  checks `shutil.which("claude")` before calling; raises `RuntimeError` on missing CLI or non-zero returncode; no `import anthropic`

`ollama>=0.6` added to `pyproject.toml` dependencies and `uv.lock` updated.

## Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| test_classifier.py | 5 | PASS |
| test_adapters.py | 5 | PASS |
| **Total** | **10** | **GREEN** |

## Deviations from Plan

### Context from Phase 03-00

`tests/test_classifier.py` and `tests/test_adapters.py` were already committed in phase 03-00 (commit `db5a769`). The TDD RED phase was confirmed by running the existing tests against missing modules, then implementing GREEN. No deviation in behavior — the tests matched the plan spec exactly.

## Decisions Made

1. `ClaudeAdapter` uses `subprocess.run(["claude", "-p", ...])` — no `anthropic` SDK import. Required by Max plan constraint (no API key available).
2. `OllamaAdapter` default host is `http://host.docker.internal:11434` — correct for macOS Docker Desktop DevContainer. Linux needs `--add-host=host.docker.internal:host-gateway`.
3. `classify()` frontmatter field wins over keyword scan — explicit user declaration takes priority over heuristic detection.
4. `ClaudeAdapter` passes `--allowedTools ""` to limit Claude subprocess tool access (AI-10 isolation).
5. `shutil.which` guard in `ClaudeAdapter` raises clear `RuntimeError` when `claude` CLI not on PATH rather than letting `subprocess.run` raise an opaque `FileNotFoundError`.

## Self-Check: PASSED

All created files confirmed on disk. Both task commits confirmed in git log:
- `d015cc6` feat(03-01): implement PII classifier
- `3da368f` feat(03-01): implement adapter base class, OllamaAdapter, ClaudeAdapter
