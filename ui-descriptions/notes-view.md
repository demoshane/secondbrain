# Notes View

## Intent
The primary workspace for reading and editing individual notes. Combines a note browser (Sidebar), the note content (NoteViewer), and note metadata/context (RightPanel). This is the default landing view.

## Layout
Three-column horizontal split: Sidebar (left, 224px) + NoteViewer/NoteEditor (center, flex-1) + RightPanel (right, 256px).

When no note is selected, the center shows "Select a note" placeholder.

---

## NoteViewer

**Intent:** Read a note and manage its metadata (tags, people, attachments, action items) inline. The reading and light editing surface.

**Components:**
- **Note toolbar** (above viewer, in App.tsx): Upload button (attach file) + Delete button (red trash icon). Both disabled when no note is open.
- **Note title** — displayed as rendered markdown header from note body.
- **Body** — rendered markdown using `@uiw/react-md-editor` in preview mode. Supports GFM (tables, checkboxes, code blocks).
- **Edit button** — pencil icon, switches to NoteEditor mode.
- **Tags section** — horizontal row of tag badges. Each tag is clickable (filters sidebar). A `+` icon button adds a new tag via TagAutocomplete. An existing tag can be clicked to enter edit mode (rename). **Issue: the `+` has no label — users don't know it adds a tag.**
- **People section** — horizontal row of person name badges. Each person name is clickable (opens their person note). A `+` icon adds a person via PersonAutocomplete. **Issue: same unlabelled `+` problem as tags.**
- **Attachments section** — list of attached files with paperclip icon. Shown only when attachments exist.
- **Action Items section** — list of action items extracted from this note. Uses ActionItemList component (checkboxes, assignee picker, due date).

**Behavior:**
- Tags are saved immediately on add/remove via PUT to `/notes/:path`.
- People are saved immediately. Adding a person creates a backlink in their person profile file.
- Clicking a tag badge in the viewer sets a tag filter in the sidebar.

---

## NoteEditor

**Intent:** Full markdown editing of note body. Replaces NoteViewer body when Edit is clicked.

**Components:**
- `@uiw/react-md-editor` in edit mode — split-pane markdown editor with live preview.
- **Save button** — saves body content. Marks note as dirty while unsaved changes exist.
- **Cancel button** — discards changes and returns to viewer mode.

**Known issues:**
- The editor takes the full center column; tags/people/attachments are not visible while editing.
- No auto-save; unsaved changes are silently lost if user navigates away.
- The MDEditor library is heavy and has styling that clashes with the app's dark mode.

---

## Known issues (Notes View overall)
- The three-panel layout is not responsive — becomes very cramped below ~1200px wide.
- Delete and Upload are icon-only buttons with no labels in the toolbar.
- No breadcrumb or path indicator showing which folder the current note is in.
- Tags `+` and People `+` are bare plus icons with no accessible label or tooltip explaining their function.
