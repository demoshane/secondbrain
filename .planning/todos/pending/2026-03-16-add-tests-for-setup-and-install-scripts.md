---
created: 2026-03-16T15:36:11.646Z
title: Add tests for setup and install scripts
area: testing
files:
  - scripts/bootstrap.py
  - scripts/install_native.py
  - scripts/install_subagent.py
---

## Problem

All three setup/install scripts (bootstrap, install_native, install_subagent) are untested. These are critical for user onboarding and native macOS integration (launchd, PATH registration) — fragile code with no safety net.

## Solution

Add unit tests mocking subprocess calls, filesystem operations, and environment checks. Test launchd plist generation, PATH registration logic, and bootstrap environment checks.
