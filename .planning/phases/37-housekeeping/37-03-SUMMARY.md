---
phase: 37-housekeeping
plan: 03
status: complete
---

# 37-03 Summary — People chips in NoteViewer

## What was done
Added people chips to NoteViewer with add/remove interaction, created PersonAutocomplete component, and added a people-only PUT branch in api.py.

## Changes
- `frontend/src/components/PersonAutocomplete.tsx` (new): Fetches /persons, filters by typed value excluding existing, stores path on selection, displays title.
- `frontend/src/components/NoteViewer.tsx`: Added `localPeople`/`addingPerson` state, `savePeopleFieldLevel()` with optimistic update+revert, people chips row (data-testid="people-chips") below tag chips.
- `engine/api.py`: Added people-only PUT branch — updates frontmatter, `notes.people` column, and `note_people` junction table (DELETE + INSERT OR IGNORE).

## Note on data model
Plan said store `name`, but `notes.people` stores paths (per LEARNINGS.md). PersonAutocomplete displays `title`, stores `path` — consistent with existing data model.

## Verification
- `npx tsc --noEmit` — clean
- Pre-existing test_delete_endpoint_404 failure unchanged
