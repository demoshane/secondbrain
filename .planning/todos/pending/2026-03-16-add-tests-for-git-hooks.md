---
created: 2026-03-16T15:36:11.646Z
title: Add tests for git hooks
area: testing
files:
  - engine/hooks/post_commit.py
  - engine/hooks/__init__.py
---

## Problem

`engine/hooks/post_commit.py` is untested. Post-commit automated note capturing can fail silently with no test safety net.

## Solution

Add unit tests mocking git commands. Test `get_commit_info()`, `main()`, and error/edge cases (no git repo, empty commit, etc.).
