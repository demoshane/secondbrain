---
phase: 32-architecture-hardening
plan: "06"
title: "People graph correctness"
status: complete
started: 2026-03-22
completed: 2026-03-22
---

# Plan 32-06: People Graph Correctness — Summary

## What was built

- engine/people.py with list_people_with_metrics() shared service (ARCH-10)
- /people API and sb_list_people MCP both call shared function — identical output (ARCH-10)
- People matched by both path AND exact title (case-insensitive) via note_people junction table (ARCH-11)
- sb-reindex --entities merges extracted people with frontmatter (not overwrite) (ARCH-12)
- update_note() re-extracts entities on body change, merges into people+entities columns + junction table (ARCH-13)

## Commits
- `0988659` feat(32-06): shared people service, path+title matching, entity merge

## Self-Check: PASSED
