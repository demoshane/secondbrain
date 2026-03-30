---
phase: 44-ai-provider-settings
plan: "03"
subsystem: settings-ui
tags: [groq, switch, settings-modal, ask-brain, toast, frontend]
dependency_graph:
  requires:
    - phase: "44-01"
      provides: GroqAdapter, router extensions
    - phase: "44-02"
      provides: Flask Groq endpoints, provider field in /ask
  provides:
    - SettingsModal AI Provider section (Groq key, all-local, feature toggles)
    - Switch component
    - AskBrainModal fallback toast
  affects: []
tech_stack:
  added: ["@radix-ui/react-switch (via shadcn Switch)"]
  patterns: [shadcn-component, sonner-toast, controlled-switch-state]
key_files:
  created:
    - frontend/src/components/ui/switch.tsx
  modified:
    - frontend/src/components/SettingsModal.tsx
    - frontend/src/components/AskBrainModal.tsx
decisions:
  - "shadcn installed switch to wrong @/ path — copied manually to src/components/ui/switch.tsx"
  - "Used toast.warning() for fallback toast — consistent with existing sonner pattern in codebase"
  - "groq-settings GET/PUT wired into global Save flow (Promise.all) — not a separate Save button"
metrics:
  duration_seconds: 420
  completed_date: "2026-03-30"
  tasks_completed: 2
  files_modified: 3
---

# Phase 44 Plan 03: Settings UI (Switch + AI Provider section + Fallback Toast) Summary

Switch component installed, SettingsModal gains full AI Provider section (Groq key save/remove/auto-test, all-local toggle, 4 feature toggles), AskBrainModal shows amber warning toast when fallback provider was used.

## Tasks Completed

| # | Name | Commit | Files |
|---|------|--------|-------|
| 1 | Install Switch + build AI Provider section in SettingsModal | 46da7c7 | frontend/src/components/ui/switch.tsx, frontend/src/components/SettingsModal.tsx |
| 2 | AskBrainModal fallback provider toast | 231482a | frontend/src/components/AskBrainModal.tsx |

## What Was Built

**Switch component** (`frontend/src/components/ui/switch.tsx`): Standard shadcn Switch built on `@radix-ui/react-switch`. Already in node_modules. Manually placed at correct path after shadcn CLI resolved the alias literally.

**SettingsModal AI Provider section**: Full section added before existing "AI model routing" block. Three subsections:
- **Groq API key**: Unconfigured shows password Input + "Save key" button; configured shows green "Configured" badge, inline connectivity result (Connected/Invalid key), "Remove key" button. Auto-runs POST /config/groq/test after successful save.
- **All-local mode**: Switch toggle. When ON, wraps feature toggles in `opacity-50 pointer-events-none`.
- **Groq feature routing**: 4 toggle rows (Ask Brain, Follow-up questions, Weekly digest, Person insights). Hidden entirely when no key configured. Disabled when all-local ON.

State loaded on modal open via GET /config/groq and GET /config/groq-settings. groq-settings persisted via global Save button (added to existing Promise.all).

**AskBrainModal fallback toast**: Checks `data.provider === 'fallback'` after successful /ask response; calls `toast.warning('Groq unavailable — used fallback model', { duration: 4000 })`. Follows sonner pattern used throughout the codebase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] shadcn CLI resolved @/ alias literally**

- **Found during:** Task 1 — shadcn install step
- **Issue:** `npx shadcn add switch` created the file at `frontend/@/components/ui/switch.tsx` instead of `frontend/src/components/ui/switch.tsx`. The CLI resolved the `@/components/ui` alias from `components.json` as a literal path segment.
- **Fix:** Read the generated file and wrote it manually to the correct path `frontend/src/components/ui/switch.tsx`.
- **Files modified:** `frontend/src/components/ui/switch.tsx`
- **Commit:** 46da7c7

## Known Stubs

None — all new UI is fully wired to real API endpoints from Plan 02.

## Self-Check: PASSED

- frontend/src/components/ui/switch.tsx: FOUND
- frontend/src/components/SettingsModal.tsx contains "AI Provider": FOUND
- frontend/src/components/SettingsModal.tsx contains groqConfigured: FOUND
- frontend/src/components/SettingsModal.tsx contains allLocal: FOUND
- frontend/src/components/SettingsModal.tsx contains config/groq fetch calls: FOUND
- frontend/src/components/SettingsModal.tsx contains config/groq-settings fetch calls: FOUND
- frontend/src/components/SettingsModal.tsx contains handleSaveGroqKey: FOUND
- frontend/src/components/SettingsModal.tsx contains handleRemoveGroqKey: FOUND
- frontend/src/components/SettingsModal.tsx contains config/groq/test: FOUND
- frontend/src/components/SettingsModal.tsx contains opacity-50 pointer-events-none: FOUND
- frontend/src/components/SettingsModal.tsx contains CheckCircle2 and XCircle: FOUND
- frontend/src/components/AskBrainModal.tsx contains data.provider: FOUND
- frontend/src/components/AskBrainModal.tsx contains "Groq unavailable": FOUND
- frontend/src/components/AskBrainModal.tsx contains toast import: FOUND
- frontend/src/components/AskBrainModal.tsx contains duration: 4000: FOUND
- TypeScript compiles clean (0 errors): PASSED
- Commits 46da7c7, 231482a: present in git log
