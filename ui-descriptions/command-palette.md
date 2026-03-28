# Command Palette

## Intent
Keyboard-first navigation and action launcher. Opens with Cmd+K. Lets the user jump to any page, open any note by name, or trigger capture actions without touching the mouse.

## Appearance
Full-screen dark overlay + centred modal panel. Input at top, grouped results list below.

## Components
- **Search input** — filters all items as you type. Placeholder: "Type a command or search..."
- **Navigation group** — one entry per page view (Notes, Actions, People, Meetings, Projects, Links, Intelligence, Inbox). Selecting navigates to that view.
- **Notes group** — all notes in the brain listed by title. Selecting opens the note in Notes view.
- **Capture group** — "Quick Capture" (opens NewNoteModal) and "Smart Capture" (opens SmartCaptureModal).
- **Empty state** — "No matching notes or commands."

## Behavior
- Keyboard-navigable with arrow keys; Enter selects.
- Clicking the overlay closes the palette.
- Powered by `cmdk` library.

## Known issues
- Notes group is flat — all notes mixed together without folder or type context, making it hard to distinguish two notes with similar titles.
- Navigation and Notes groups have the same visual weight — commands and notes are hard to tell apart when mixed in search results.
- No recent/frequently-used items shown when input is empty.
- Cmd+K shortcut is not surfaced anywhere in the UI — undiscoverable for new users.
