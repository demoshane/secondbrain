# Phase 41.2 — Improvements & Fixes Backlog

Items to address during or after 41.2 execution.

---

## Sidebar: collapse two-level grouping to single-level by type

**File:** `frontend/src/components/Sidebar.tsx`

**Problem:** Notes are currently grouped folder → type (two levels). This creates redundant labels like "Note > Note" (folder `notes/`, type `note`) and confusing ones like "Person > Note" (folder `person/`, type `note`). The folder structure mirrors the type taxonomy almost exactly, making the outer level noise.

**Fix:** Replace `groupByFolderThenType` with a single `groupByType`. Flatten the render from two nested `CollapsibleSection`s to one. Update `sectionId` keys (currently `sidebar-folder-type`) accordingly.

**Impact:** Sidebar becomes a clean single-level type list. No data loss — type field carries all the semantic info the folder did.

---

## Chrome extension: UI refresh according to design visuals

**File:** `chrome-extension/popup.html`, `chrome-extension/popup.css`, `chrome-extension/popup.js`

**Request:** Improve the Chrome plugin UI to match the visual design language established for the main app.

**Blocker:** No Chrome-specific visual found in `ui-design-files/`. Need user to clarify which visual/mockup to reference before planning this task.

---

## Action items: interactive everywhere they appear

**Context:** Person detail view (and other views) show action items as plain bullet text under "Open Items". The DB-backed `action_items` table has structured records but the NoteViewer renders them as raw markdown only.

**Request:** Wherever action items are visible, the user should be able to:
1. Mark an item done (checkbox toggle)
2. Add a deadline to an item (date picker or inline input)
3. Add a new action item in context (inline form)

**Affected views:** PeoplePage person detail (Actions section), RightPanel (already has ActionItemRow — extend with deadline), NoteViewer (action items rendered from markdown are not interactive — needs DB-backed rendering), MeetingsPage detail (Actions already added in 41.2-02 — add deadline support).

**Backend:** `PUT /actions/<id>` likely needs a `due_date` field. `ActionItem` type needs `due_date` added. `ActionItemRow` component needs deadline display + inline date input.
