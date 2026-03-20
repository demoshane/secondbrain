# Phase 29: Link Capture — Host Verification Plan

## Pre-requisites [HOST]
```bash
cd ~/second-brain/frontend && npm run build
cd ~/second-brain && uv tool install . --reinstall
launchctl kickstart -k gui/$(id -u)/com.secondbrain.api
```

## 1. Links tab visible
- Open `http://localhost:5001/ui` (or sb-gui)
- Confirm "Links" tab in tab bar

## 2. Empty state
- Click Links tab with no links captured
- Expect: "No links saved yet — use sb_capture_link in Claude"

## 3. Capture a link via MCP
```
sb_capture_link(url="https://react.dev", tags=["react", "docs"], notes="React documentation")
```
- Expect: `status: "created"`, title fetched from og:title

## 4. Link appears in list
- Refresh Links page
- Confirm: title, domain (react.dev), date, tags (react, docs), description

## 5. Detail panel
- Click the link row
- Confirm: title, domain, date, body, "Visit Link" button, "Open in Notes" button
- Tags displayed with X (remove) and + (add) buttons

## 6. Visit Link
- Click "Visit Link" — browser opens react.dev

## 7. Open in Notes
- Click "Open in Notes" — switches to Notes view with the link note selected

## 8. Upsert (re-capture same URL)
```
sb_capture_link(url="https://react.dev", tags=["react", "updated"], notes="Updated description")
```
- Expect: `status: "updated"` (not duplicate_warning)
- Confirm tags and description updated in Links page

## 9. Title editing
- Click title in detail panel → edit inline → Enter to save
- Confirm title updates in both detail and sidebar list

## 10. Tag editing
- Double-click a tag → rename → Enter
- Click + → add new tag → Enter
- Hover tag → click X to remove
- All changes persist on page refresh

## 11. Body editing
- Hover body area → click Edit button
- Modify text → click Save
- Confirm changes persist

## 12. Security: javascript: URL blocked
- If you have a link with non-http URL, "Visit Link" should do nothing

## 13. Tests [CONTAINER]
```bash
uv run pytest tests/ -q --ignore=tests/test_gui.py --ignore=tests/test_preflight.py
```
- All pass, no isolation failures

## 14. Playwright GUI tests [HOST]
```bash
uv run pytest tests/test_gui.py -q
```
