# Claude Learnings — Second Brain Project

Persistent log of bugs, rules, and learnings.
Claude must update this file whenever a bug is diagnosed and fixed, or a recurring pattern is identified.

---

## RULE: Always Read LEARNINGS.md Before Starting Work

**Root cause:** CLAUDE.md did not mandate reading LEARNINGS.md, so project-specific rules (correct port, deploy pipeline, Playwright-first policy) were ignored, wasting user time.

**Fix:** Added to CLAUDE.md: read LEARNINGS.md before any implementation, debugging, or testing; update it after every resolved issue.

**Rule:** Read `.claude/LEARNINGS.md` at the start of every session before touching any code or tests.

---

## RULE: Never Perform Destructive Actions Without Explicit Permission

### Destructive actions — ask first

**Destructive = hard to reverse or affects shared/external state.** Examples:
- `rm`, `rmdir` — deleting files or directories
- `git reset --hard`, `git clean`, `git push --force` — destructive git ops
- `DROP TABLE`, `DELETE FROM` — database mutations
- `uv tool uninstall`, package removals
- Overwriting files that weren't explicitly targeted

**Terminating processes (`kill`, `pkill`) is OK** — no need to ask.

**Rule:** Always describe the destructive action and ask for confirmation BEFORE running it.

---

### Secrets — absolutely forbidden

Never read, log, print, expose, or share secret values. This includes:
- API keys, tokens, passwords, credentials
- `.env` files, `secrets.baseline`, credential JSON files
- Private keys, certificates
- Any value that looks like a secret even if not explicitly labelled

**Rule:** If a file or value might contain secrets, do not output its contents. Reference the file path only.

---

### Working outside allowed folders — ask first

Allowed folders for this project:
- `/Users/tuomasleppanen/second-brain/` (primary repo)
- `/Users/tuomasleppanen/SecondBrain/` (brain data directory)
- `/Users/tuomasleppanen/.claude/` (Claude config)
- `/Users/tuomasleppanen/Library/LaunchAgents/` (launchd agents)

**Rule:** Before reading, writing, or executing anything outside these folders, clearly explain WHY it's needed and ask for explicit permission. Never assume it's OK.

---

## Frontend Changes — Full Deploy Pipeline Required

**Symptom:** Frontend changes appear in source but are invisible in the running GUI.

**Root cause:** The GUI is served by the installed `uv tool` binary, not the dev source tree.
Three separate caches must all be updated:
1. The compiled static bundle in `engine/gui/static/`
2. The installed tool's copy of those files
3. The in-memory process serving requests

**Fix — run in order after any `frontend/src/**` change:**
```bash
# 1. Rebuild bundle
cd /Users/tuomasleppanen/second-brain/frontend && npm run build

# 2. Reinstall uv tool (copies new static files into installed location)
cd /Users/tuomasleppanen/second-brain && uv tool install . --reinstall

# 3. Restart the running API (kills old in-memory process)
kill $(lsof -ti :37491) 2>/dev/null; sleep 1
/Users/tuomasleppanen/.local/bin/sb-api > /tmp/sb-api.log 2>&1 &
sleep 3
```

**GUI URL:** `http://localhost:37491/ui` (NOT port 5001)

**Rule:** Any plan touching `frontend/src/**` must include this deploy pipeline as a task before any Playwright tests or human-verify checkpoint.

---

## Stale sb-api / sb-watch Processes

**Symptom:** Code changes have no effect; old behavior persists after edits.

**Root cause:** launchd or a manually started process is running the old installed binary.
The installed binary lives at `/Users/tuomasleppanen/.local/share/uv/tools/second-brain/`.

**Fix:**
```bash
# Check what's running
launchctl list | grep second-brain
lsof -i :37491 | grep LISTEN

# Kill and reinstall
kill $(lsof -ti :37491) 2>/dev/null
uv tool install . --reinstall
/Users/tuomasleppanen/.local/bin/sb-api &
```

**Rule:** When debugging unexpected behavior, always check for stale processes FIRST before investigating code.

---

## Missing Reinstall After Frontend Commit — GUI Tab Not Visible

**Symptom:** A new tab (e.g. Projects) is correctly added in source (`TabBar.tsx`, `App.tsx`) and
committed with a new JS bundle, but the tab does not appear when running `uv run sb-gui`.

**Root cause:** `uv run sb-gui` starts the Flask sidecar from source (`engine/api.py`), and
`_STATIC_DIR` resolves correctly to the source tree. However, if a stale `sb-api` process is
already listening on port 37491 (started from the previously installed binary), `gui/__init__.py`
detects the open port and reuses that process — which still serves the old installed bundle
(`index-BhpHLrjv.js` with no Projects tab). The reinstall step (`uv tool install . --reinstall`)
was skipped after the build commit, so the installed package had the old static files.

**Fix:**
```bash
kill $(lsof -ti :37491) 2>/dev/null
/Users/tuomasleppanen/.local/bin/uv tool install . --reinstall
/Users/tuomasleppanen/.local/bin/sb-api > /tmp/sb-api.log 2>&1 &
```

**Diagnosis steps:**
1. Check installed `index.html`: `cat ~/.local/share/uv/tools/second-brain/lib/python3.14/site-packages/engine/gui/static/index.html`
2. If it references an old bundle hash → reinstall is missing.
3. Check if stale process exists: `lsof -i :37491 | grep LISTEN`

**Rule:** After any frontend build commit, always run `uv tool install . --reinstall` AND
restart sb-api before testing. The "stale process reuse" path in `gui/__init__.py` means
a running old sb-api silently bypasses the source static files entirely.

---

## Bug: compute_health_score() Called With Wrong kwarg — Health Score Shows "..."

**Symptom:** Brain Health score stuck at "..." in IntelligencePage; `/brain-health` returns 500.

**Root cause:** `api.py` called `compute_health_score(empty=len(empty), ...)` but the function signature uses `orphans` as the parameter name (not `empty`). The `empty` count was being passed where `orphans` count was expected, and `orphans` was omitted entirely.

**Fix:** Changed `empty=len(empty)` to `orphans=len(orphans)` in the `brain_health_endpoint` call in `engine/api.py`.

**Rule:** When calling functions with keyword arguments, always verify parameter names match the function signature exactly — especially after adding new computed values (like `empty_notes`) that could cause accidental name collisions.

---

## Bug: RightPanel Fetched Non-Existent Endpoints — Backlinks and People Empty

**Symptom:** RightPanel showed nothing (no backlinks, no people) after phase 27.7-02 cleanup.

**Root cause:** `RightPanel.tsx` was fetching `/notes/${encoded}/backlinks` and `/notes/${encoded}/people` — two endpoints that have never existed in `api.py`. The correct endpoint is `/notes/<path>/meta` which returns `{ backlinks, related, people }` in a single response.

**Fix:** Replaced both separate fetches with a single fetch to `/notes/${encoded}/meta`, reading `.backlinks` and `.people` from the combined response.

**Rule:** Before wiring a frontend component to an API endpoint, verify the route exists in `engine/api.py`. The only note metadata endpoint is `/notes/<path>/meta`.

---

## Playwright Testing — Always Test Before Presenting to User

**Rule:** Never present a human-verify checkpoint without first confirming the feature works via Playwright.

**How:**
```python
# Navigate to the app
browser_navigate("http://localhost:37491/ui")
# Take snapshot to confirm UI state
browser_snapshot()
# Interact with the feature under test
browser_click(ref=...)
```

**Why:** User time is wasted if the feature is broken before they even look at it.

---
