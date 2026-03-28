---
plan: 42-03
status: complete
---

## Summary

Added importance to the frontend: badge component, sidebar badges + sort toggle, NoteViewer badge, RightPanel dropdown.

**Changes:**
- `frontend/src/types.ts`: Added `importance?: string` to Note interface.
- `frontend/src/components/ui/importance-badge.tsx`: New `ImportanceBadge` component with HIGH/MED/LOW labels and red/yellow/grey dark-palette colors.
- `frontend/src/components/Sidebar.tsx`: Added `useState` import, `ImportanceBadge` import, `IMPORTANCE_ORDER` map, `sortByImportance` state, sort logic, toggle button above scroll area, and ImportanceBadge render in NoteRow.
- `frontend/src/components/NoteViewer.tsx`: Added `ImportanceBadge` import and render in metadata row next to NoteTypeBadge.
- `frontend/src/components/RightPanel.tsx`: Added `notes` to context destructuring, `importance` state, useEffect to sync from current note, importance dropdown UI above backlinks section.

**Verification:** `npx tsc --noEmit` exits 0, no TypeScript errors.
