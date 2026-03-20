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

## Bug: People Section in RightPanel Shows Header But No Names

**Symptom:** People section renders the "People" header but all badges are blank (no text).

**Root cause:** `notes.people` column stores a JSON array of file paths (e.g. `["/Users/.../people/olli-erinko.md"]`). The `/notes/<path>/meta` endpoint returned these raw path strings directly. `RightPanel.tsx` treats the response as `Note[]` and reads `.title`, which is `undefined` on a plain string.

**Fix:** In `engine/api.py` `note_meta()`, after parsing `raw_people`, look up each path in the `notes` table to get `{path, title}`. Fall back to stem-derived title if the path isn't indexed.

**Rule:** The `people` field in `notes` is a list of paths, not objects. Any endpoint returning people data must resolve those paths to `{path, title}` objects before sending to the frontend.

---

## Bug: Brain Health Score 0/100 — Orphan Detection Too Aggressive

**Symptom:** Brain Health page shows score 0/100 and reports nearly all notes as orphaned.

**Root cause:** `get_orphan_notes()` used `LEFT JOIN relationships r ON n.path = r.target_path` — a note was considered connected only if something linked *to* it (inbound). Notes that link *outward* (appear as `source_path`) but have no inbound links were also flagged as orphans. In practice, most notes have outbound links but few have inbound links, so nearly everything was orphaned and the score collapsed to ~0.

**Fix:** Changed the query to use `NOT IN (SELECT source_path ... UNION SELECT target_path ...)` — a note is connected if it appears in *either* direction in `relationships`.

**Rule:** "Orphan" means no relationship in either direction (neither source nor target). Do not check only one side of the relationship table.

---

## Bug: Brain Health Score 0/100 — Formula Multiplied By 100 Twice

**Symptom:** Brain Health page shows score 0/100 even after orphan detection was fixed.

**Root cause:** `compute_health_score()` had `return max(0, round(100 - penalty * 100))` where `penalty` is already computed as a sum of `ratio * weight` (e.g. `orphan_ratio * 30`). The weights (30, 40, 20) are point deductions on a 0-100 scale, so `penalty` is already in `[0, 90]`. Multiplying by 100 again produces a value like `2960`, making the score clamp to 0 for any non-trivial orphan count.

**Fix:** Removed the `* 100` — formula is now `return max(0, round(100 - penalty))`.

**Correct formula:** `penalty = (orphan_ratio * 30) + (broken_ratio * 40) + (dup_ratio * 20)` — each weight is the max points that category can deduct. Score = `100 - penalty`. Do NOT scale by 100 again.

**Rule:** When writing a score formula with ratio × weight where weights sum to ~100, do NOT multiply the total penalty by 100. The weights ARE the points.

---

## Bug: RightPanel Backlinks and People Were Not Clickable

**Symptom:** Backlinks shown as plain `<div>` text, people shown as `<Badge>` with no click handler — neither navigated to the linked note.

**Root cause:** `RightPanel.tsx` rendered both sections without `onClick` handlers. The `openNote` function from `NoteContext` was not wired up.

**Fix:** Changed backlink `<div>` to `<button onClick={() => openNote(b.path)}>` with `data-testid="backlink-item"`. Changed people `<Badge>` to add `onClick={() => openNote(p.path)}` with `cursor-pointer hover:bg-accent` styles and `data-testid="people-badge"`.

**Rule:** Any item in RightPanel that represents a navigable note must use `openNote(path)` from `useNoteContext()`. Use `<button>` for list items (not `<div>`); add `cursor-pointer` to Badge clicks.

---

## Bug: sb-reindex Inflated Note Count — Stale DB Entries + Hidden-Dir Files Indexed

**Symptom:** DB had 577 notes but only ~334 actual `.md` files on disk. Count never shrank even after deleting notes.

**Root causes (two):**
1. `reindex_brain()` only upserted files found on disk — it never deleted DB rows for files that had been removed. Ghost entries accumulated indefinitely.
2. `rglob("*.md")` traversed hidden directories (`.meta/`, `.index/`, `.claude/`) and indexed digests, templates, and config-adjacent files that are not real notes.

**Fix (`engine/reindex.py`):**
- Before the walk loop, build `disk_paths: set[str]` of all non-hidden `.md` files (skipping files where any parent path component starts with `.`).
- After the initial FTS rebuild, compute `stale_paths = db_paths - disk_paths` and DELETE from `notes`, `note_embeddings`, `relationships`, `action_items` for each stale path. Rebuild FTS again.
- The walk loop itself also skips hidden-directory files using the same guard.

**Result:** 577 → 334 notes after one `sb-reindex` run (273 stale entries purged).

**Rule:** `reindex_brain()` must always purge DB rows whose paths are absent from disk. Hidden directories (any path component starting with `.`) must be excluded from the walk — they contain metadata, not user notes.

---

## Bug: People Not Showing in Right Panel — Body-Mention Detection Missing

**Symptom:** Right panel PEOPLE section is empty even when person notes exist and people are mentioned by name in the note body.

**Root causes (three compounding):**

1. **`people: []` in frontmatter at capture time** — The `people` field is only populated if explicitly passed at capture; entity extraction runs but stores results only in the `entities` column, not back into `people`.

2. **Entity extraction misses Finnish/non-ASCII names** — `_extract_people()` in `entities.py` uses `[A-Z][a-z]+` (ASCII only). Names with ä/ö/etc. (e.g. "Jaana Tanskanen", "Tuomas Leppänen") are not matched.

3. **`note_meta()` only resolved `raw_people`** — The endpoint resolved whatever was in the `people` DB column. For notes where that column is `[]`, it returned an empty list even when person notes existed whose titles appeared in the body.

**Fix (`engine/api.py` `note_meta()`):**
- Added a "body-mention detection" pass: after resolving `raw_people`, fetch all person notes (`type IN ('person', 'people')`) and check if each title appears (case-insensitive) in the note body.
- Also hardened the `raw_people` resolver to handle both absolute paths and plain name strings.
- Deduplication via `seen_paths` set ensures no duplicate entries.

**Rule:** The meta endpoint must detect people by body-mention as a fallback. Never rely solely on the `people` column — it may be `[]` for notes captured before entity extraction was working, or for notes with non-ASCII names that bypass the regex.

---

## Bug: Test Suite Writing to Real ~/SecondBrain — Missing DB_PATH + BRAIN_ROOT Patches

**Symptom:** After running `pytest`, stale test notes (`batch-note-*.md`, `dedup-test-note*.md`, `good-note*.md`) appear in `~/SecondBrain/note/`.

**Root causes (three distinct patterns):**

1. **`tmp_note` / `tmp_note_pair` fixtures in `test_api.py`** — Set `BRAIN_PATH` via `monkeypatch.setenv` but never patched `engine.db.DB_PATH` or `engine.paths.DB_PATH`. Every `get_connection()` call fell back to the real `~/SecondBrain/.meta/brain.db`.

2. **`tmp_api_note` fixture in `test_delete.py`** — Same pattern: `BRAIN_PATH` set but `DB_PATH` not patched.

3. **`test_sb_capture_batch`, `test_sb_capture_dedup_warning`, etc. in `test_mcp.py`** — No isolation fixture at all. Called `mcp_mod.sb_capture_batch()` directly. Inside `sb_capture_batch`, `BRAIN_ROOT` was re-imported locally via `from engine.paths import BRAIN_ROOT as _BRAIN_ROOT` — so patching only `mcp_mod.BRAIN_ROOT` was insufficient. The local re-import read from `engine.paths.BRAIN_ROOT` which was not patched.

**Fix:**
- Add `monkeypatch.setattr(engine.db, "DB_PATH", tmp_db)` + `monkeypatch.setattr(engine.paths, "DB_PATH", tmp_db)` to every fixture that calls `get_connection()` without an explicit path.
- For MCP capture tests: also patch `engine.paths.BRAIN_ROOT` (not just `mcp_mod.BRAIN_ROOT`) because `sb_capture_batch` re-imports `BRAIN_ROOT` from `engine.paths` locally at call time.
- Added `_guard_real_brain` session-scoped autouse fixture in `conftest.py` that snapshots `~/SecondBrain/*.md` mtimes before and after the session and fails loudly if any new files appear.

**Rule:** Any test fixture that calls `get_connection()` without an explicit path MUST patch both `engine.db.DB_PATH` and `engine.paths.DB_PATH`. Any test that calls MCP capture functions MUST also patch `engine.paths.BRAIN_ROOT` (not just `mcp_mod.BRAIN_ROOT`), because those functions re-import `BRAIN_ROOT` from `engine.paths` at call time.

---

## Bug: Container npm ci Corrupts Host node_modules — Cross-Platform Native Binaries

**Symptom:** `npm run build` on host fails with `Cannot find native binding @rolldown/binding-darwin-x64` after running devcontainer.

**Root cause:** `frontend/node_modules/` is shared via bind mount. Container runs `npm ci` which installs Linux native binaries (e.g. `@rolldown/binding-linux-x64`). These overwrite the macOS binaries the host needs. Next host build fails because darwin binaries are gone.

**Fix:** Added a named Docker volume (`frontend-node-modules`) that shadows `/workspace/frontend/node_modules` inside the container. Container gets its own isolated Linux `node_modules`, host's macOS `node_modules` is never touched.

**Rule:** Any platform-specific binary directory shared between host and container via bind mount MUST be isolated with a named volume. This applies to `node_modules` (native extensions) and `.venv` (Python, already isolated via `UV_PROJECT_ENVIRONMENT`).

---

## Bug: Entity Extraction Greedy Regex Consumes Stop-Word Pairs — Second Word Lost

**Symptom:** "Met Anna Korhonen" extracts nothing for "Anna Korhonen" after "Met" is added to stop words.

**Root cause:** `re.findall()` with a greedy two-word pattern consumes both words of a match before the stop-word filter runs. "Met Anna" is matched and filtered out, but "Anna" has already been consumed — the engine won't re-attempt from "Anna" to match "Anna Korhonen".

**Fix:** Replace `re.findall()` with `re.finditer()` and manual position tracking. When the first word of a match is a stop word, set `pos = m.start(2)` (start of the second group) and `continue` — the engine retries from there, matching "Anna Korhonen" next.

**Rule:** When filtering multi-word regex matches on the first token, use `re.finditer` with manual position retry on stop-word hits. `re.findall` does not allow partial consumption.

---

## Bug: ensure_person_profile() Fails When brain_root/person/ Missing

**Symptom:** `capture_note()` raises `FileNotFoundError` on first capture to a fresh brain_root that doesn't have the `person/` subdirectory created yet.

**Root cause:** `ensure_person_profile()` in `engine/links.py` calls `person_file.write_text()` without first creating the parent directory.

**Fix:** Add `person_file.parent.mkdir(parents=True, exist_ok=True)` before `write_text()`.

**Rule:** Always call `parent.mkdir(parents=True, exist_ok=True)` before writing a new file — never assume subdirectories exist in `brain_root`.

---

## Pattern: People Write-Back Requires Entity Extraction Before build_post()

**Symptom:** `people` column in DB remains `[]` even though entity extraction runs at capture time.

**Root cause:** The original capture order was `build_post(people=[]) → extract_entities() → write_note_atomic()`. The `post["people"]` field was already set to `[]` by `build_post()`; entity extraction only set `post["entities"]` and never updated `people`.

**Fix:** New order: `extract_entities(title, body) → merge_people → build_post(merged_people) → write_note_atomic()`.

**Rule:** Any field that must be populated from entity extraction MUST be computed BEFORE calling `build_post()`. The `people` parameter to `build_post()` is written verbatim to frontmatter and DB — it cannot be patched after the fact without a second UPDATE.

---
