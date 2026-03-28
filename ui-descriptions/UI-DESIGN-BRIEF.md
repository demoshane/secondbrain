# Second Brain — UI Design Instructions

You are designing the complete UI for **Second Brain**, a personal knowledge management desktop application. Use this document as your full specification. Design all screens and components described below.

---

## Product Overview

Second Brain is a desktop app for capturing, searching, and surfacing personal notes. Notes are markdown files with metadata (tags, people, type). The app has a CLI, a desktop GUI, and an MCP server for AI integrations.

**Primary users:** Knowledge workers who capture meeting notes, ideas, projects, and people profiles. The app surfaces connections and action items automatically from note content.

**Design principles:**
- Minimal chrome — navigation is infrastructure, content is king
- Zero friction for capture
- Keyboard-first, but fully mouse-operable
- Dense information where needed; no unnecessary whitespace
- Dark mode as default

---

## Technology Context

- React frontend, dark mode
- Component library: your choice (Tailwind recommended)
- Desktop window (not mobile) — minimum 1280px wide
- Markdown rendering throughout (GFM: tables, checkboxes, code blocks)

---

## App Shell

Design the persistent chrome that wraps every view.

**Layout:** Full-height flex column:
1. **Topbar** (fixed height, always visible)
2. **TabBar** (fixed height, always visible)
3. **Content area** (fills remaining height)

Content area for the Notes view only: three-column horizontal split — Sidebar (left) + main content (flex) + Right Panel (right). All other views: single full-width content area.

### Topbar

Design requirements:
- Left: app logo/name
- Center: search input (magnifier icon, placeholder "Search notes…"). Enter searches, Escape clears.
- Right: three action buttons — **New Note** (labeled), **Smart Capture** (sparkles icon + label "Smart Capture"), **Batch Capture** (icon + label "Batch")
- Far right: connection status indicator (green/amber dot with tooltip: "Connected" / "Disconnected")
- Hide the search mode selector (Hybrid/BM25/Semantic) behind an advanced options toggle — it's expert-only noise

### TabBar

Eight tabs: **Notes · Actions · People · Meetings · Projects · Intelligence · Inbox · Links**

Design requirements:
- Each tab has an icon + label
- Active tab: distinct highlight (bottom border or background pill)
- Consider grouping: primary (Notes, Inbox) · content types (People, Meetings, Projects) · tools (Actions, Intelligence, Links)
- Tabs must not overflow/wrap at 1280px minimum width

---

## Sidebar (Notes view only)

Fixed 256px width, left column of the Notes three-column layout.

Design requirements:
- Note browser grouped by folder, then by type within each folder
- Each group level is collapsible with a chevron
- Show note count badge on each folder and type header
- Active note highlighted
- **Tag filter mode:** when a tag filter is active, replace the full list with filtered results and show a dismissible banner at the top ("Filtered by: [tag name] ×")
- **Search mode:** when a topbar search is active, show search results instead of full list
- Resizable width (drag handle on right edge)
- Titles that overflow should show a tooltip on hover

---

## Right Panel (Notes view only)

Fixed 256px width, right column of the Notes three-column layout. Collapsible.

Design requirements:
- Three sections stacked vertically: **Backlinks** · **People** · **Action Items**
- Each section: heading + content. Hidden when empty.
- **Backlinks:** list of clickable note titles that link to the current note
- **People:** row of clickable person name badges — clicking opens their profile
- **Action Items:** list with checkbox, action text, assignee dropdown, due date
- When all three sections are empty: show a helpful empty state ("No connections yet — add tags or link this note to others")
- Collapse button: chevron on the panel's left edge, collapses to a thin icon strip

---

## Notes View

Default landing view. Three-column layout: Sidebar + content + Right Panel.

### NoteViewer

Reading and metadata surface for an open note.

Design requirements:
- **Toolbar** at top: Upload attachment button (icon + "Attach") · Delete note button (red, icon + "Delete"). Disabled when no note is open.
- **Note title** — large, prominent, from the note's markdown h1
- **Body** — rendered markdown, comfortable reading width, not full-column
- **Edit** button — pencil icon, top-right of body area, switches to NoteEditor
- **Tags row** — tag badges below body. "Add tag" button (+ icon with label "Add tag"). Each badge: click to filter sidebar, hover to show remove ×.
- **People row** — person name badges. "Add person" button (+ icon with label "Add person"). Each badge: click to open profile.
- **Attachments** — show only when attachments exist. Each file: icon + name + download link.
- **Action Items** — extracted items with checkbox, text, assignee, due date. "No action items" empty state.
- When no note is selected: centered empty state "Select a note or create a new one"

### NoteEditor

Full markdown editing. Replaces viewer body when Edit is clicked.

Design requirements:
- Split-pane: editor (left) + live preview (right)
- Tags and People sections remain visible below the editor (not hidden during edit)
- **Save** button (primary) + **Cancel** button (secondary)
- Dirty indicator: "Unsaved changes" badge near Save
- Auto-save after 3s of inactivity (with subtle indicator)
- Warn before navigation if unsaved changes exist

---

## Command Palette

**Trigger:** Cmd+K (visible keyboard shortcut hint in Topbar)

Design requirements:
- Full-screen dim overlay + centred floating panel (max 600px wide)
- Search input at top with "Type a command or search…" placeholder
- Results in grouped sections:
  - **Recent** (shown when input empty) — 5 recently opened notes
  - **Go to** — navigation entries: Notes, Actions, People, Meetings, Projects, Links, Intelligence, Inbox. Each with an icon.
  - **Notes** — matching notes listed by title + folder path for disambiguation
  - **Capture** — "New Note" and "Smart Capture" actions
- Keyboard navigation: arrow keys move selection, Enter activates, Escape closes
- Click overlay to close
- Empty state: "No results for '[query]'"

---

## Modals

Design a consistent modal system. All modals share: dark overlay, centred panel, close button (×), Escape to close.

### New Note Modal
- Title input (autofocused, Enter submits)
- Type selector: note / idea / meeting / person / project / strategy (pill or segmented control)
- Optional body textarea (collapsed by default, expandable)
- **Create** button (primary) · **Cancel** (secondary)

### Smart Capture Modal
- Explanation: "Paste anything — meeting notes, ideas, a conversation. AI will turn it into structured notes."
- Large textarea (min 200px height), placeholder with example content
- **Capture** button (primary, with sparkles icon)
- **Results view** (replaces form after capture): list of created notes, each with type badge + title + "Open" link. Error items shown with warning icon + message.
- "Capture more" button to go back to the form

### Batch Capture Modal
- File picker or multi-item text input
- Preview of items to be created
- **Import** button + **Cancel**

### File Upload Modal
- Drag-and-drop zone + "Browse" fallback
- Selected file name shown before upload
- **Attach** button + **Cancel**

### New Entity Modal (shared by Meetings and Projects)
- Title input
- Type shown as read-only label (Meeting / Project)
- **Create** button + **Cancel**

### Delete Modals (Note and Entity)
- Destructive style: red accent, warning icon
- Explicit confirmation text: "Delete '[name]'? This cannot be undone."
- **Delete** button (red) · **Keep** button (primary)

---

## Actions Page

**Intent:** Centralised to-do list from all action items extracted across all notes.

**Layout:** Single-column, full height. Sticky filter bar at top, scrollable list below.

Design requirements:
- **Filter bar:** Status dropdown (Open / Done / All, default: Open) · Assignee dropdown (All / per-person) · search/filter input
- **Action item row:**
  - Checkbox (large, clickable — toggles done/open with strikethrough animation on done)
  - Action text (strikethrough when done)
  - Source note link: "from [note title]" in muted style — clickable, opens note in Notes view
  - Assignee: compact dropdown or "Unassigned" with assign button
  - Due date: compact date picker or "No date"
  - Delete: icon button, hover-reveal, opens confirmation dialog
- Group items by: source note (default) or due date (toggle)
- **Empty state (all done):** celebratory message "All clear! No open action items."
- **Empty state (filtered):** "No items match your filters."
- "New Action" button in filter bar to create a standalone action item (not tied to a note)

---

## People Page

**Intent:** Directory of all people in the brain with full context panel.

**Layout:** Two-column: people list (left, 320px) + person detail (right, flex).

### People List
- Search input at top
- "New Person" button
- Table: **Name** · **Notes** (backlink count) · **Actions** (open count)
- Selected row highlighted
- Clickable rows

### Person Detail
Empty state: "Select a person."

When selected:
- Person name as large heading
- Action buttons: "Open in Notes" · "Delete" (red, hover-reveal or confirmation-required)
- **Profile** section: rendered markdown of their profile note. Inline Edit button.
- **Meetings** (collapsible): meeting titles as clickable links + date
- **Notes** (collapsible): backlink note titles as clickable links
- **Action Items** (collapsible): open actions with interactive checkboxes + due dates

Design improvements over current:
- Avatar/initials badge next to name
- "New Person" button in the list panel (not requiring a separate flow)
- Terminology: use "People" consistently throughout

---

## Meetings Page

**Intent:** Structured view of meeting notes — find a meeting by date or participant, review outcomes.

**Layout:** Two-column: meeting list (left, 320px) + meeting detail (right, flex).

### Meeting List
- Filter input
- "New Meeting" button
- Table: **Title** · **Participants** · **Date** · **Actions** · delete (hover-reveal, confirmed)
- Sortable columns (Date descending by default)
- Selected row highlighted

### Meeting Detail
Empty state: "Select a meeting."

When selected:
- Meeting title heading + "Open in Notes" button
- **Notes** (collapsible): rendered markdown body
- **Participants** (collapsible): person name badges, each clickable → opens person profile
- **Action Items** (collapsible): **interactive** checkboxes — mark done directly from this panel
- **Backlinks** (collapsible): note titles as **clickable links**

---

## Projects Page

**Intent:** Structured view of project notes — status at a glance, actions and related notes.

**Layout:** Two-column: project list (left, 320px) + project detail (right, flex). Mirrors Meetings page structure.

### Project List
- Filter input
- "New Project" button
- Table: **Title** · **Status** (Active / Paused / Completed — editable inline badge) · **Updated** (relative time, e.g. "2 days ago") · **Actions** · delete (hover-reveal, confirmed)
- Sortable columns

### Project Detail
Empty state: "Select a project."

When selected:
- Project title + status badge (editable) + "Open in Notes" button
- **Notes** (collapsible): rendered markdown body
- **Action Items** (collapsible): interactive checkboxes
- **Related Notes** (collapsible): backlink titles as **clickable links**
- **Linked Meetings** (collapsible): meetings linked to this project

---

## Intelligence Page

**Intent:** Brain health dashboard + daily awareness. Answer: "What does my brain need from me right now?"

**Layout:** Two-column: left column (2/3 width) for health and stale items, right column (1/3 width) for recap and quick actions.

### Left Column

**Brain Health card:**
- Health score prominently displayed (large number /100 with colour: green ≥80, amber 50–79, red <50)
- Score explains itself: e.g. "Good — 3 issues found" not just "82"
- Four collapsible sub-sections, each with count badge:
  - **Orphaned Notes** — no incoming links, no tags/people. Each title clickable. "Ignore" per-item.
  - **Empty Notes** — no body. Each title clickable + inline Delete.
  - **Broken Links** — `source → missing target` pairs. Source clickable. "Repair all" button.
  - **Duplicate Candidates** — pairs with similarity %. Both titles clickable. Merge / Smart Merge per pair. "Smart Merge All" bulk action.
- Collapse state persisted across visits

**Stale Notes card:**
- Notes not touched in >30 days (threshold configurable)
- Title + last-updated relative date. Titles clickable. "Archive" / "Dismiss" per item.

### Right Column

**Recap card:**
- "Generate Recap" button (sparkles icon)
- Generated summary displayed as rendered markdown
- Timestamp of last generation

**Action Items card:**
- Top 5 overdue or oldest open action items (shared ActionItemList)
- "View all" link → Actions page

**Quick Capture card:**
- Single-field fast capture input ("Capture a thought…" placeholder, Enter submits)

**Chrome Extension card** (collapsible, collapsed by default):
- API status dot + setup instructions

---

## Inbox Page

**Intent:** GTD-style triage queue. Goal: get to zero.

**Layout:** Two-column: triage list (left, 340px) + note preview (right, flex).

### Triage List

**Header:** Item count badge, or "All clear ✓" with last-checked time.

Three collapsible sections:

**Unassigned Actions:**
- Filter by source note (debounced input)
- Each card: action text · source note title (not absolute path) · assignee dropdown · "Assign & Dismiss" button
- Pagination: load 20 at a time

**Unprocessed Notes** (recently captured, no links or tags):
- Criteria shown: "Captured in the last 7 days with no tags or backlinks"
- Each card: title · captured date · "Add Backlink" (expands inline picker) · tag input · "Done" button
- "Done" = note has been reviewed (mark as processed, remove from inbox)

**Empty Notes:**
- Each card: title · Created date · "Open" · "Delete" · "Keep"
- "Delete all empty" button with confirmation

### Note Preview (right column)
Selected item: read-only NoteViewer.
Empty state: "Select an item from the list to preview it."
**Keyboard navigation:** arrow keys move between items in the list.

---

## Links Page

**Intent:** Library of saved web links with captured metadata.

**Layout:** Two-column: link list (left, 320px) + link detail (right, flex).

### Link List
- Search input (filters title and description)
- Active tag filter badge (dismissible)
- Each item: **Title** · domain (muted) · date · description (2-line truncated) · tag badges
- Clicking a tag badge sets the filter
- Clicking the row opens the detail panel
- Multi-tag filter (AND logic)

### Link Detail
Empty state: "Select a link."

When selected:
- Title as heading + domain badge + date
- "Visit Link" button (primary, external link icon) — opens URL in browser
- Tag badges with inline edit (add/remove tags)
- Body: rendered **markdown** (not plain text)
- Edit title button
- Delete link button (with confirmation)
- "Open as Note" button — navigates to the underlying note in Notes view

---

## Shared Components

### ActionItemList
Used on: Actions page, Right Panel, Intelligence page, People/Meetings/Projects detail panels.

- Checkbox (large, interactive — toggles done/open)
- Action text (strikethrough when done)
- Assignee: compact dropdown
- Due date: compact date picker — overdue dates shown in red
- Delete: hover-reveal icon button

### CollapsibleSection
Used throughout detail panels.

- Heading + count badge + chevron
- Smooth collapse/expand animation
- State persisted to localStorage by section ID

### EmptyState
Used wherever a list or panel can be empty.

- Icon + title + optional description + optional action button
- Consistent visual style throughout

### ConfirmDialog
Used for all destructive actions.

- Destructive variant: red accent, warning icon
- Non-destructive variant: neutral
- Always names the thing being acted on: "Delete 'Meeting notes 2024-03-15'?"
- Two buttons: confirm (matches action verb) + cancel

---

## Global UX Patterns

Apply these consistently across all screens:

1. **Terminology:** Use "People" everywhere — not "Persons". Use "Notes" not "Note files".
2. **Clickable titles:** Every note title, person name, and meeting title in every list or panel must be a clickable link to its canonical view.
3. **Interactive action items:** Checkboxes on action items are always interactive — never display-only.
4. **Relative timestamps:** Show "2 days ago", "last week" — not raw ISO dates. Full date on hover tooltip.
5. **Hover-reveal destructive actions:** Delete buttons are always hover-reveal with a confirmation step.
6. **Labeled controls:** No icon-only controls without a visible label or persistent tooltip. Exceptions: universally recognised icons (× for close, magnifier for search).
7. **Keyboard shortcuts:** Surface Cmd+K prominently. Add tooltip shortcuts to all primary actions.
8. **Section state persistence:** Collapse/expand state of all sections persists across visits via localStorage.
9. **Empty states:** Every empty state includes an explanation and a primary next action (not just a blank area).
10. **Loading states:** All async operations show a skeleton or spinner — never a blank flicker.
