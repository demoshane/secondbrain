---
status: diagnosed
phase: 01-foundation
source: 01-00-SUMMARY.md, 01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md, 01-06-SUMMARY.md
started: 2026-03-14T14:00:00Z
updated: 2026-03-14T15:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. pytest suite passes
expected: Run `python -m pytest tests/ -v` inside the container. All tests pass or skip — zero failures. Exit code 0.
result: issue
reported: "1 failed, 30 passed — tests/test_precommit.py::test_blocks_api_key AssertionError: Expected detect-secrets to flag the API key"
severity: minor

### 2. bootstrap.py --dev all green
expected: Run `python scripts/bootstrap.py --dev` inside the container. Every check shows [PASS] — Drive folder writable, .env.host present, python-frontmatter installed, Python >= 3.12. Exit message: "All checks passed."
result: issue
reported: "python-frontmatter [FAIL] when run as `python scripts/bootstrap.py` — installed in venv but bootstrap uses system Python; fix is to run via `uv run python scripts/bootstrap.py --dev`"
severity: minor

### 3. /sb-init idempotent on existing brain
expected: Run `uv run sb-init` a second time. All 9 dirs show [EXISTS] (not [CREATED]). Schema initializes idempotently — no errors. `.vscode/settings.json` confirmed [OK].
result: pass

### 4. /sb-reindex on empty brain
expected: Run `uv run sb-reindex` inside the container. Output: `[OK] Indexed 0 notes` and `[sb-reindex] Done.` — no errors, no tracebacks.
result: pass

### 5. Bind mount write test
expected: Inside container: `echo "test" > /workspace/brain/uat-test.md`. On host macOS terminal: `ls -la ~/SecondBrain/uat-test.md` — file visible, owned by your macOS user (not root). Clean up: `rm ~/SecondBrain/uat-test.md`.
result: pass

### 6. .env.host absent from git
expected: Run `git status` on host or inside container. `.env.host` does NOT appear in tracked, staged, or untracked files. Only `.env.host.example` is visible in the repo.
result: pass

### 7. Pre-commit hook blocks secrets
expected: Already verified during 01-06 (RSA private key commit was blocked). Confirm: `cat .git/hooks/pre-commit` exists and references detect-secrets.
result: issue
reported: "Hook exists but hardcodes macOS Homebrew Python path (/usr/local/opt/pre-commit/libexec/bin/python3.14); host and container overwrite each other on `pre-commit install`; inside container, fallback `command -v pre-commit` also fails — commits from container would fail with 'pre-commit not found'"
severity: major

## Summary

total: 7
passed: 4
issues: 3
pending: 0
skipped: 0

## Gaps

- truth: "bootstrap.py --dev reports all checks green inside the container"
  status: failed
  reason: "User reported: python-frontmatter [FAIL] when invoked as `python scripts/bootstrap.py` — uses system Python, not venv; fix: bootstrap should be invoked via `uv run` or check should use venv Python"
  severity: minor
  test: 2
  root_cause: "README.md line 73 and bootstrap.py docstring line 7 both say `python scripts/bootstrap.py --dev` — this uses system Python which lacks python-frontmatter. The package is only installed in the uv venv. Also need venv detection warning in the script itself."
  artifacts:
    - path: "README.md"
      issue: "line 73: instructs bare `python` instead of `uv run python`"
    - path: "scripts/bootstrap.py"
      issue: "line 7: docstring says bare `python`; no venv detection guard in main()"
  missing:
    - "Update README.md line 73 to use `uv run python scripts/bootstrap.py --dev`"
    - "Update docstring in scripts/bootstrap.py"
    - "Add venv detection warning near top of main() if sys.prefix == sys.base_prefix"

- truth: "pytest suite exits 0 with zero failures"
  status: failed
  reason: "User reported: 1 failed, 30 passed — test_blocks_api_key expects detect-secrets to flag sk-ant-api03-* key but no Anthropic plugin exists"
  severity: minor
  test: 1
  root_cause: "test_precommit.py::test_blocks_api_key uses low-entropy fake value (FAKEFAKEFAKE...) which heuristic filters discard. No Anthropic plugin exists in detect-secrets. Test should be changed to test detectable secret types (AWS key, RSA header) and add separate test documenting the Anthropic key limitation."
  artifacts:
    - path: "tests/test_precommit.py"
      issue: "lines 27-35: test_blocks_api_key asserts detect-secrets catches sk-ant-api03-* key, which it cannot"
  missing:
    - "Replace test_blocks_api_key with test using a known-detectable secret type (e.g. AWS key or private key header)"
    - "Add test_anthropic_key_not_detected to document known limitation"

- truth: "pre-commit hook works correctly inside the container"
  status: failed
  reason: "Hook hardcodes macOS Homebrew Python path; host/container installs overwrite each other; inside container commits fail with 'pre-commit not found'"
  severity: major
  test: 7
  root_cause: ".git/hooks/pre-commit line 6 hardcodes INSTALL_PYTHON=/usr/local/opt/pre-commit/libexec/bin/python3.14 (Homebrew path). Container runs `uv run pre-commit install` in postCreateCommand which overwrites the hook; then host `pre-commit install` overwrites it back. Inside container, Homebrew path doesn't exist and `pre-commit` is not on bare PATH (it's in uv venv), so both branches of the hook's fallback logic fail."
  artifacts:
    - path: ".git/hooks/pre-commit"
      issue: "line 6: INSTALL_PYTHON hardcoded to Homebrew path; lines 13-20: fallback `command -v pre-commit` fails in container"
    - path: ".devcontainer/devcontainer.json"
      issue: "line 36: postCreateCommand runs `uv run pre-commit install` which overwrites host-installed hook"
  missing:
    - "Create .githooks/pre-commit portable wrapper script that tries `uv run pre-commit run --hook-stage pre-commit` (works in both envs)"
    - "Set `git config core.hooksPath .githooks` in postCreateCommand instead of `pre-commit install`"
    - "Remove `uv run pre-commit install` from postCreateCommand; keep hooks in .githooks/ versioned in repo"
