# Phase 27 — Open TODOs

> **Important:** When executing this phase, re-audit the codebase for any new gaps (untested modules, missing features, broken integrations) that have accumulated since this was written. All identified gaps must be included in scope — not just the items pre-listed here.

## Test Coverage Gaps

- [ ] **LLM Adapters** — add tests for `engine/adapters/base.py`, `claude_adapter.py`, `ollama_adapter.py` (mock Claude API + Ollama; test adapter selection/routing)
- [ ] **Setup scripts** — add tests for `scripts/bootstrap.py`, `install_native.py`, `install_subagent.py` (test launchd plist generation, PATH registration, env checks)
- [ ] **Health checks** — add tests for `engine/health.py` (verify all ~8 check functions)
- [ ] **Git hooks** — add tests for `engine/hooks/post_commit.py` (mock git commands, verify post-commit behavior)
- [ ] **CI pipeline** — add GitHub Actions workflow to run `pytest` on push/PR to catch regressions automatically
