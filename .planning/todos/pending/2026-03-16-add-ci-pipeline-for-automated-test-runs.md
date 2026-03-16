---
created: 2026-03-16T15:36:11.646Z
title: Add CI pipeline for automated test runs
area: tooling
files:
  - .github/workflows/
  - pyproject.toml
---

## Problem

No CI/CD pipeline exists. Tests only run when manually invoked — regressions can slip into main undetected.

## Solution

Add GitHub Actions workflow to run `pytest` on push and PRs. Optionally add pytest-cov and fail on coverage drop below a threshold.
