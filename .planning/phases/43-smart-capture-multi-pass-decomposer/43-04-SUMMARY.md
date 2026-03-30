---
phase: 43-smart-capture-multi-pass-decomposer
plan: 04
subsystem: frontend/components
tags: [smart-capture, settings-modal, action-item-markers, person-stubs, gui]
dependency_graph:
  requires: [43-01, 43-02, 43-03]
  provides: [SettingsModal Capture section, SmartCaptureModal person stubs display]
  affects: [frontend/src/components/SettingsModal.tsx, frontend/src/components/SmartCaptureModal.tsx]
tech_stack:
  added: []
  patterns: [parallel fetch on modal open, TYPE_COLORS.person reuse, isDuplicate inline validation]
key_files:
  created: []
  modified:
    - frontend/src/components/SettingsModal.tsx
    - frontend/src/components/SmartCaptureModal.tsx
decisions:
  - "DEFAULT_MARKERS constant in SettingsModal — hard-coded client-side, not fetched from backend; reduces API complexity for read-only system defaults"
  - "Person stubs section rendered below saved notes list — display-only, no navigation; Phase 44 may add click-to-open"
  - "Link notes flow into existing saved list via type:link badge — no structural change to SavedNote rendering needed"
  - "isDuplicate check is case-insensitive against both DEFAULT_MARKERS and customMarkers — prevents silent duplicates"
metrics:
  duration: 1
  completed_date: 2026-03-29
  tasks: 2
  files_modified: 2
status: complete
date: 2026-03-29
---

# Phase 43 Plan 04: GUI — SettingsModal Capture Section + SmartCaptureModal Stubs

**One-liner:** Added action-item marker CRUD to SettingsModal and person stub display to SmartCaptureModal — completing the user-facing Phase 43 GUI surface.

## What was built

### Task 1: SettingsModal Capture section (d74ed3f)

Added a "Capture" section below the Ollama section in `SettingsModal.tsx`:

- `DEFAULT_MARKERS = ['TODO', 'AP', 'action:', '@owner', 'Action Point']` — shown as non-removable chips
- `customMarkers` state loaded from `GET /config/action-item-markers` on modal open (non-fatal, parallel with config fetch)
- Custom markers rendered as removable chips with `X` button and `aria-label`
- Add-marker input with Enter key support; `isDuplicate` inline validation (case-insensitive, destructive border + disabled button)
- `handleSave` fires `PUT /config/action-item-markers` in parallel with routing save
- `X` icon added to lucide-react import

### Task 2: SmartCaptureModal person stubs display (453e8ba)

Updated `SmartCaptureModal.tsx` to surface decomposer outputs:

- `PersonStub` interface: `{name: string, type: string, path?: string}`
- `personStubs` state extracted from `POST /smart-capture` response `person_stubs` field
- State reset on modal close and on capture error
- Rendered below saved notes list: `User` icon + person badge (reuses `TYPE_COLORS.person`) + name
- Link notes: no change needed — `type: "link"` already flows into existing saved notes list with link badge colour

## Deviations from Plan

None — both tasks implemented exactly as specified. TypeScript compilation passes.

## Self-Check: PASSED

- SettingsModal.tsx: `"Capture"` section header — FOUND
- SettingsModal.tsx: `"Action-item markers"` label — FOUND
- SettingsModal.tsx: `DEFAULT_MARKERS` array — FOUND
- SettingsModal.tsx: `config/action-item-markers` fetch URL — FOUND
- SettingsModal.tsx: `customMarkers` state — FOUND
- SettingsModal.tsx: `isDuplicate` — FOUND
- SettingsModal.tsx: `aria-label` Remove marker — FOUND
- SmartCaptureModal.tsx: `person_stubs` API field access — FOUND
- SmartCaptureModal.tsx: `personStubs` state — FOUND
- SmartCaptureModal.tsx: `"person stub"` display text — FOUND
- SmartCaptureModal.tsx: `User` icon import — FOUND

## Awaiting: Human Verify (Task 3)

Run `make dev` then verify the 9-step UAT in 43-04-PLAN.md Task 3.
