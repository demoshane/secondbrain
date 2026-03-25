---
created: 2026-03-16T13:46:41.990Z
title: Audit and improve context detection on capture
area: general
files: []
---

## Problem

Two related gaps in the proactive capture flow:

1. **Context detection not triggering.** The second brain system is supposed to identify high-value contexts in conversation (people, meetings, projects, decisions) and offer to capture them. In practice this has not been observed — e.g. during Cowork discussions, no capture offer appeared for people mentioned.

2. **Cascade capture missing.** When capturing a note (e.g. a meeting), the system should detect referenced entities that don't yet exist as notes (people, projects) and offer to create those too — in a single flow rather than requiring separate manual captures.

## Solution

- Audit `sb_capture` and the proactive capture instructions in `second-brain.md` to confirm the detection logic is implemented and firing correctly.
- If detection is missing: implement NER-style scanning of note body at capture time to surface unresolved person/project references.
- Add cascade prompt: after saving a meeting/discussion note, list any mentioned names or projects that have no matching note and offer to create stub notes for each.
- Verify against a real Cowork-style conversation as acceptance test.
