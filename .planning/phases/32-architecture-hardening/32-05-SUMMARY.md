---
phase: 32-architecture-hardening
plan: "05"
title: "Security + consistency fixes"
status: complete
started: 2026-03-22
completed: 2026-03-22
---

# Plan 32-05: Security + Consistency Fixes — Summary

## What was built

- PERSON_TYPES constant in db.py, replaces hardcoded ('person','people') across api.py, mcp_server.py, segmenter.py (ARCH-16)
- _escape_like() helper in db.py for safe LIKE patterns (ARCH-14)
- move_file() path traversal guard — 403 on paths outside BRAIN_ROOT (ARCH-07)
- forget_person() DB-first cascade with people JSON cleanup in surviving notes + frontmatter (ARCH-08)
- Logging cleanup: bare except:pass → logging.warning in intelligence.py; print → logging.warning in search.py (ARCH-09)

## Commits
- `0cbf3b0` feat(32-05): PERSON_TYPES constant, _escape_like helper, move_file path guard
- `38697a6` feat(32-05): forget_person DB-first cascade, people cleanup, logging fixes

## Self-Check: PASSED
