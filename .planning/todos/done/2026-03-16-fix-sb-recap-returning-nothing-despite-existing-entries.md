---
created: 2026-03-16T11:48:03.083Z
title: Fix sb-recap returning nothing despite existing entries
area: general
files: []
---

## Problem

`sb-recap` (recap my week) returns "No task completed - no recap available" even when there are many entries in the second brain. The GUI shows this message and Claude says "the Second Brain doesn't have enough captured context from this week." This is wrong — the user has plenty of notes captured.

Root cause is unknown — likely a date filter issue (recap may be filtering by a date range that doesn't match the stored note timestamps), or the recap command queries a specific field (e.g. "completed tasks") rather than all recent notes.

Screenshot context: user typed "recap my week so far", got "No task completed - no recap available", then asked "How come? I just added a new file so second brain should have context?"

## Solution

1. Investigate what `sb-recap` queries — does it filter by a specific field or date range?
2. Check if note timestamps are stored in UTC vs local time (could cause week boundary mismatch)
3. Check if recap only looks at "tasks" note type vs all note types
4. Compare what `sb-search` returns for this week vs what recap sees
