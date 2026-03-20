# Plan 31-05 Summary: Smart Capture GUI Modal

## Status: Complete

## What was built
- `POST /smart-capture` Flask route in `engine/api.py` — segments freeform text, saves atomically, creates co-captured relationships, triggers SSE refresh
- `SmartCaptureModal.tsx` — two-phase UI: paste area with Capture button, then results list with type-colored badges (meeting=blue, person=green, project=purple, idea=yellow, link=cyan, note=gray)
- Topbar Sparkles icon button opens the modal
- App.tsx state management and modal wiring

## Key decisions
- Auto-save (no confirm step) — consistent with sb_capture_smart MCP behavior
- Results phase shows what was created; user clicks "Done" to close
- Entity people extracted from segments and passed to capture_note

## Commits
- `9985bac` feat(31-05): Smart Capture GUI modal + POST /smart-capture API
