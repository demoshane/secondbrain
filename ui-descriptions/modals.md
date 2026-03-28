# Modals

## New Note Modal
**Trigger:** "New Note" button in Topbar, or Quick Capture in Command Palette.
**Intent:** Create a new note with a title and type. Opens the new note immediately after creation.
**Fields:** Title (text input, Enter submits) · Type (dropdown: note / idea / meeting / person / project / strategy).
**Known issues:** No body pre-fill; no folder selection — note lands in default location determined by type.

---

## Smart Capture Modal
**Trigger:** Sparkles icon in Topbar, or Smart Capture in Command Palette.
**Intent:** Paste freeform text (meeting notes, conversation dumps) and let AI parse it into one or more typed notes automatically. Zero-friction capture when structure isn't known upfront.
**Flow:**
1. Large textarea for pasting content.
2. "Capture" button triggers AI analysis.
3. Results screen shows list of created notes, each with type badge and title. Errors shown inline.
**Known issues:** No way to review or edit AI-proposed notes before they're saved — capture is irreversible from this modal. No link to open the created notes.

---

## Batch Capture Modal
**Trigger:** Folder-sync icon in Topbar.
**Intent:** Capture multiple notes at once from structured input (e.g. a list of items).
*(Implementation details in BatchCaptureModal.tsx — not read in full.)*

---

## File Upload Modal
**Trigger:** Upload icon in Notes view toolbar (requires a note to be open).
**Intent:** Attach a file to the currently open note. File is stored and linked to the note.
*(Implementation details in FileUploadModal.tsx — not read in full.)*

---

## New Entity Modal
**Trigger:** "New Meeting" button on Meetings page, "New Project" button on Projects page.
**Intent:** Create a new meeting or project note with the correct type metadata. Shared modal component parameterised by `entityType`.

---

## Delete Note Modal
**Trigger:** Red trash icon in Notes view toolbar.
**Intent:** Confirm deletion of the currently open note. Destructive, irreversible.

---

## Delete Entity Modal
**Trigger:** Delete button on People, Meetings, or Projects page detail panel.
**Intent:** Confirm deletion of a person/meeting/project note. Shared component parameterised by `entityType` and `entityName`.

---

## Known issues (modals overall)
- No consistent visual language distinguishing destructive modals (delete) from creative ones (new note, capture).
- Smart Capture and New Note are two separate flows — no unified "capture" experience.
- No keyboard shortcut shown in modal headers for power users.
