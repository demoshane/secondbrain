---
created: 2026-03-16T15:36:11.646Z
title: Add tests for health checks
area: testing
files:
  - engine/health.py
---

## Problem

`engine/health.py` has ~8 check functions (brain directory, database, FTS index, embeddings, launchd, etc.) with no tests. Diagnostic tools users rely on are unvalidated.

## Solution

Add unit tests for each check function, mocking filesystem/DB state to simulate healthy and failing conditions.
