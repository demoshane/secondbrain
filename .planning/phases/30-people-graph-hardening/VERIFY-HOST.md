# Phase 30-04 — Verification Plan (HOST)

Run this on your HOST Claude Code session: `/sb-verify-phase 30`

---

## 1. Build + Reinstall

```bash
source "$HOME/.nvm/nvm.sh"
cd /Users/tuomasleppanen/second-brain/frontend && npm run build

cd /Users/tuomasleppanen/second-brain
uv tool install . --reinstall

kill $(lsof -ti :37491) 2>/dev/null; sleep 1
/Users/tuomasleppanen/.local/bin/sb-api > /tmp/sb-api.log 2>&1 &
sleep 3
```

---

## 2. Backend Test Suite

```bash
cd /Users/tuomasleppanen/second-brain
uv run pytest tests/ -q
```

Expected: all tests green (2 xfail allowed).

---

## 3. API Verification

```bash
curl -s http://localhost:37491/people | python3 -m json.tool
```

Expected response shape:
```json
{
  "people": [
    {
      "path": "...",
      "title": "...",
      "updated_at": "YYYY-MM-DD",
      "open_actions": 0,
      "org": "",
      "last_interaction": null,
      "mention_count": 0
    }
  ]
}
```

Each person object must contain: `org`, `last_interaction`, `mention_count` fields.

---

## 4. Playwright GUI Tests

```bash
cd /Users/tuomasleppanen/second-brain
uv run pytest tests/test_gui.py -k people -v
```

Expected: People page tests pass (row click, detail pane visible).

---

## 5. Manual Visual Verification

Open `http://localhost:37491/ui` and navigate to the People tab.

**Left pane table — expected columns:**
- Name
- Org (shows org name or `—`)
- Last Interaction (shows date YYYY-MM-DD or `—`)
- Actions (shows count badge or `—`)

**Detail pane — when a person is selected:**
- Header shows person name
- Sub-header shows Organization, Last Interaction, Mentions stats
- Sections: Note, Meetings, Backlinks, Open Actions

**Finnish/Unicode name rendering:**
- If any notes contain Finnish names (e.g. "Tuomas Leppänen"), they should render correctly in the table.

**Person type coverage:**
- Notes with `type: person` appear in the table.
- Notes with `type: people` (group notes) also appear in the table.
- Notes with `type: note` or any other type do NOT appear.

---

## 6. Known Deviations

- Meetings detection in detail pane: uses `meta.meetings` from API if available;
  falls back to type-field filtering on backlinks. The `/notes/<path>/meta` endpoint
  does not currently return a `meetings` key, so the fallback path is used — meetings
  section may be empty unless the API is extended in a future phase.
