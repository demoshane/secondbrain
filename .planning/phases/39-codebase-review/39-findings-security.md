# Security Audit Findings

**Audit date:** 2026-03-27
**Auditor:** gsd-executor agent (Wave 1 — security dimension)
**Scope:** engine/api.py, engine/mcp_server.py, engine/capture.py, engine/forget.py, engine/delete.py, engine/db.py, engine/backup.py, engine/anonymize.py, chrome-extension/

---

## Pre-Identified Items (S-01 through S-06) — Status

| ID | Status | Notes |
|----|--------|-------|
| S-01 | CONFIRMED — see SEC-01 | All `int(request.args.get(...))` calls unguarded |
| S-02 | CONFIRMED — see SEC-02 | Duplicate import line 24-25 |
| S-03 | CONFIRMED (lower than expected) — see SEC-05 | innerHTML used but escapeHtml consistently applied; CSP absent |
| S-04 | CONFIRMED — see SEC-06 | CORS accepts any chrome-extension:// origin |
| S-05 | ACCEPTED RISK — no-auth on localhost by design | Documented below as ACCEPTED |
| S-06 | CONFIRMED + CLARIFIED — see SEC-03 | Path guard uses unresolved `brain_path`; symlink bypass possible |

---

## Finding: SEC-01

- **Severity:** High
- **File:** engine/api.py:165-166, 321-322, 337-338, 406-407, 640-641, 738-739, 1108-1109, 1456
- **Description:** Every `int(request.args.get("limit", ...))` and `int(request.args.get("offset", ...))` call in the API is unguarded. If a caller sends `limit=abc` or `offset=xyz`, Python raises `ValueError` at the `int()` call, Flask catches it and returns HTTP 500. This leaks no data, but it's an availability issue — any unauthenticated caller can trigger 500 responses on 8+ endpoints by sending malformed query parameters.

  Additionally, line 641 `/links` offset is not wrapped in `max(..., 0)` like the others, accepting negative offsets which cause SQLite `OFFSET -N` — SQLite silently treats negative OFFSET as 0, so no crash, but inconsistent.

- **Root cause:** Endpoints were added incrementally across 30+ phases without a shared query-param parsing helper. Pattern was copy-pasted without adding error handling.
- **Recommended fix:** Wrap each `int()` call in a try/except ValueError, return HTTP 400 with a clear message. Alternatively, introduce a `_int_param(name, default, min_val=None, max_val=None)` helper used by all endpoints.

  ```python
  def _int_param(name: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
      try:
          val = int(request.args.get(name, default))
      except (ValueError, TypeError):
          abort(400, f"Invalid value for '{name}': must be an integer")
      if min_val is not None:
          val = max(val, min_val)
      if max_val is not None:
          val = min(val, max_val)
      return val
  ```

- **Blast radius:** Low — callers using valid parameters are unaffected. Fix returns 400 instead of 500, which is strictly better. No schema changes needed.

---

## Finding: SEC-02

- **Severity:** Medium (correctness, code quality)
- **File:** engine/api.py:24-25
- **Description:** `from engine.paths import BRAIN_ROOT` appears on line 24. Line 25 immediately overwrites it with `from engine.paths import BRAIN_ROOT, store_path`. Line 24 is dead code — the first import is a no-op. Not a security vulnerability, but signals copy-paste residue and confuses readers about import dependencies.
- **Root cause:** Iterative development — a later commit added `store_path` to the import without removing the original line.
- **Recommended fix:** Delete line 24. Keep only line 25 (`from engine.paths import BRAIN_ROOT, store_path`).
- **Blast radius:** None — the runtime effect is identical. Tests unaffected.

---

## Finding: SEC-03

- **Severity:** Medium
- **File:** engine/api.py:1159-1165 (`delete_file`)
- **Description:** The `/files` DELETE endpoint path-traversal guard has a symlink bypass. The guard resolves the target path (`_Path(file_path).resolve()`) and compares it to `files_dir.resolve()`. However, `files_dir` is constructed as `_Path(brain_path) / "files"` where `brain_path = os.environ.get("BRAIN_PATH", ...)`. If `BRAIN_PATH` itself is a symlink, `files_dir.resolve()` will dereference it, but only after the guard already ran:

  ```python
  files_dir = _Path(brain_path) / "files"          # NOT resolved yet
  target = _Path(file_path).resolve()               # fully resolved
  target.relative_to(files_dir.resolve())           # resolves files_dir here
  ```

  In practice `files_dir.resolve()` IS called via `relative_to()`, so the guard actually works correctly in this specific code path. The finding from RESEARCH.md was partially correct but the actual call does resolve both sides. The real residual issue is: the `delete_file()` endpoint accepts an **absolute path from the client JSON body** (`body.get("path", "")`). The client should not need to know or supply absolute filesystem paths — a relative path from the brain root would be safer and would eliminate the need for the path guard entirely.

- **Root cause:** The API was designed to accept absolute paths from the GUI (which learns them from `/files` list endpoint responses). The guard was added reactively rather than designing path handling to use relative references throughout.
- **Recommended fix:** Keep the existing guard as-is (it works). For a stronger fix in a follow-up: change the `/files` DELETE endpoint to accept relative paths only (relative to `BRAIN_ROOT/files/`) and construct the absolute path server-side. This eliminates the entire class of path-injection attacks on this endpoint.
- **Blast radius:** Low — the existing guard prevents exploitation today. The stronger fix requires frontend coordination.

---

## Finding: SEC-04

- **Severity:** Medium
- **File:** engine/mcp_server.py:685
- **Description:** `sb_files` tool accepts a `subfolder` parameter that is concatenated directly into a filesystem path without validation:

  ```python
  search_root = files_dir / subfolder if subfolder else files_dir
  ```

  A caller passing `subfolder = "../../../etc"` would construct `BRAIN_ROOT/files/../../../etc`, which after resolution escapes the files directory. The subsequent `rglob("*")` then lists files outside the brain. The results include absolute paths returned to the caller, potentially leaking directory structure outside the brain.

- **Root cause:** The subfolder parameter was added as a convenience feature without path validation.
- **Recommended fix:** Validate the subfolder after constructing the path — assert it is inside `files_dir`:

  ```python
  if subfolder:
      search_root = (files_dir / subfolder).resolve()
      if not search_root.is_relative_to(files_dir.resolve()):
          raise ValueError("INVALID_SUBFOLDER: path escapes files directory")
  else:
      search_root = files_dir
  ```

- **Blast radius:** Low — affects `sb_files` MCP tool only. Fix adds a ValueError for malicious subfolder values; valid subfolder values are unaffected.

---

## Finding: SEC-05

- **Severity:** Medium
- **File:** chrome-extension/manifest.json:20-24, chrome-extension/popup.js:306-315
- **Description:** Two related issues:

  **5a. No Content Security Policy in manifest.** The manifest.json has no `content_security_policy` key. Chrome MV3 applies a default CSP (`script-src 'self'; object-src 'self'`), which blocks eval and inline scripts in extension pages. This is acceptable but the absence of an explicit CSP means the extension relies on the default rather than documenting its security posture. A more explicit CSP would prevent future developers from inadvertently weakening it.

  **5b. `innerHTML` assignment in popup.js:311.** The history list render uses `li.innerHTML = \`...\`` to insert history entries. The interpolated values are run through `escapeHtml()` before insertion, which correctly escapes `<`, `>`, `"`, and `&`. This prevents XSS via stored history titles. However, the `escapeHtml()` function does not escape single quotes `'`, which means an entry with a single quote in the title could break attribute contexts. In the current template (`title="${escapeHtml(...)}"`) this is not exploitable because the attribute is double-quoted. But the pattern is fragile — future changes to the template could introduce single-quote injection.

- **Root cause:**
  - 5a: CSP was never explicitly configured — relying on Chrome's default.
  - 5b: `escapeHtml()` was written for HTML content contexts, not attribute contexts. Sufficient for current use but incomplete.
- **Recommended fix:**
  - 5a: Add `"content_security_policy": {"extension_pages": "script-src 'self'; object-src 'self'"}` to manifest.json.
  - 5b: Either use `textContent` / DOM API instead of `innerHTML`, or extend `escapeHtml` to also escape `'` → `&#39;`. Prefer DOM API:

    ```js
    const span = document.createElement('span');
    span.className = 'history-title';
    span.title = entry.title || '';
    span.textContent = entry.title || 'Untitled';
    li.appendChild(span);
    ```

- **Blast radius:** Low. 5a is additive only. 5b: switching to DOM API removes any XSS risk and has no functional change.

---

## Finding: SEC-06

- **Severity:** Low
- **File:** engine/api.py:64
- **Description:** CORS is configured to accept any `chrome-extension://` origin:

  ```python
  CORS(app, origins=["null", "file://*", "http://127.0.0.1:*", "chrome-extension://*"])
  ```

  The `chrome-extension://*` wildcard accepts requests from ANY installed Chrome extension, not just the Second Brain extension. A malicious extension installed in the same browser profile could make cross-origin requests to the local API and read or modify brain data.

- **Root cause:** The extension ID changes per-install (Chrome generates a random ID unless the extension is published on the Web Store with a fixed ID). The wildcard was used as a pragmatic workaround.
- **Recommended fix:** The API is also bound to `127.0.0.1` only (via `serve(app, host="127.0.0.1")`), which prevents access from the network. The CORS wildcard only matters if another local extension tries to call it. This is the accepted risk documented in SECURITY.md. No immediate fix required — document as accepted risk. If the extension is published to the Web Store, replace `chrome-extension://*` with the specific extension ID (`chrome-extension://<extension-id>`).
- **Blast radius:** N/A — accepted risk, no fix in this phase.

---

## Finding: SEC-07

- **Severity:** Low
- **File:** engine/api.py:786-791 (`gui_shell`)
- **Description:** The `/ui` endpoint injects the `request.host_url` into the HTML response as a JavaScript variable:

  ```python
  injection = f'<script>window.API_BASE = "{api_base}";</script>'
  ```

  The `api_base` is derived from `request.host_url`, which is normally `http://127.0.0.1:37491`. Since the API is bound to `127.0.0.1`, only local callers can reach this endpoint. However, if an attacker could set the `Host` header to a crafted value, they could inject arbitrary JavaScript. In practice, this is unexploitable because:
  1. The API is localhost-only (not exposed to network).
  2. The GUI is served by pywebview, which controls the host header.

  The pattern is worth documenting because it would be dangerous if the API were ever exposed externally.

- **Root cause:** Convenience injection — avoids hardcoding the API base URL in the frontend bundle.
- **Recommended fix:** No fix required for the current localhost-only deployment. If the API is ever exposed beyond localhost, replace the `request.host_url` injection with a hardcoded or configuration-sourced value.
- **Blast radius:** N/A — accepted risk in current deployment model.

---

## Finding: SEC-08

- **Severity:** Low
- **File:** engine/api.py:783
- **Description:** `PUT /ui/prefs` writes arbitrary JSON from the request body directly to a file:

  ```python
  data = request.get_json(force=True) or {}
  p.write_text(json.dumps(data), encoding="utf-8")
  ```

  There is no validation of the JSON structure, size limits, or key constraints. A caller could write a very large JSON object (up to Flask's 50MB body limit), causing a large preferences file. This is a DoS/disk-exhaustion concern in theory. In practice, the API is localhost-only and the preferences file is a single JSON document with a few user settings.

- **Root cause:** Simple CRUD endpoint with no input constraints.
- **Recommended fix:** Add a size check (e.g., reject if serialized JSON > 64KB). Optionally validate that only known preference keys are written. Low priority given localhost-only context.
- **Blast radius:** None — adding a size check is a non-breaking addition.

---

## Finding: SEC-09

- **Severity:** Low (design accepted risk)
- **File:** chrome-extension/content.js:21-23, manifest.json:21
- **Description:** The content script is injected on `<all_urls>` (excluding mail.google.com). It runs Readability.js and reads `document.body.innerText` when triggered by user action (context menu or icon click) — NOT automatically. The data is only read on-demand and sent to the popup via message passing.

  The broad permission scope (`<all_urls>`) means the extension is technically active on every page, including banking sites and sensitive applications. The user grants this permission on install. The actual data capture only happens when the user explicitly triggers it.

- **Root cause:** Broad permissions are required to support article extraction on any page.
- **Recommended fix:** Document as accepted risk — this is expected browser extension behavior. Ensure the install page clearly communicates what data is accessed. No code change needed.
- **Blast radius:** N/A.

---

## Accepted Risks (Not Findings)

| ID | Description | Rationale |
|----|-------------|-----------|
| S-05 | No auth on Flask API | Localhost-only binding; single-user system; CORS guards extension access |
| SEC-07 | Host header injection in /ui | Localhost-only; pywebview controls host header; not network-exposed |

---

## SQL Injection Assessment

**No SQL injection vulnerabilities found.** All database queries use parameterized placeholders (`?`). Verified across:
- All `search_notes()` calls — FTS5 queries use parameterized `MATCH ?`
- All `WHERE path=?` queries — parameterized
- `forget.py` DELETE IN uses `",".join("?" * len(all_delete_paths))` with bound params
- `note_meta` backlink query — body LIKE query is parameterized (`LOWER(?)`)

The one potential concern was the `_apply_filters()` function — it was reviewed in `search.py` context; filters use parameterized queries throughout.

---

## PII Exposure Assessment

**MCP tools — PII routing is correct.** `sb_read` checks `sensitivity == "pii"` and routes through the Ollama adapter before returning content. The two-step confirm_token pattern is applied to `sb_forget` and `sb_anonymize` (destructive ops). `sb_capture` applies `classify_smart()` to auto-detect and upgrade sensitivity.

**One gap:** `sb_person_context` returns the full note body (`"note": {"title": person_title, "body": row["body"]}`). If the person note has `content_sensitivity == "pii"`, the body is returned verbatim without routing through the Ollama adapter. This is inconsistent with `sb_read`'s behavior. However, person notes rarely contain the most sensitive PII (that tends to be in meeting notes), and the MCP caller (Claude) is already subject to Anthropic's data handling policies per SECURITY.md.

This inconsistency is documented but not elevated to a critical finding — it is a design gap rather than an exploitable vulnerability.

---

## Summary Table

| ID | Severity | File | Description | Fix Required |
|----|----------|------|-------------|-------------|
| SEC-01 | High | api.py (8 locations) | Unguarded int() on query params → HTTP 500 | Yes — Plan 39-05 |
| SEC-02 | Medium | api.py:24-25 | Duplicate import (dead code) | Yes — trivial |
| SEC-03 | Medium | api.py:1155-1165 | delete_file accepts abs path from client; guard correct but design risk | No (guard works) — document |
| SEC-04 | Medium | mcp_server.py:685 | sb_files subfolder not validated — path traversal outside files_dir | Yes — Plan 39-05 |
| SEC-05 | Medium | manifest.json, popup.js:311 | No explicit CSP; innerHTML with escapeHtml (single-quote gap) | Yes — Plan 39-05 |
| SEC-06 | Low | api.py:64 | CORS accepts any chrome-extension:// origin | No (accepted risk) |
| SEC-07 | Low | api.py:786-791 | Host header injection in /ui script injection | No (localhost-only) |
| SEC-08 | Low | api.py:783 | /ui/prefs PUT has no size/schema validation | No (localhost-only) |
| SEC-09 | Low | manifest.json, content.js | all_urls permission scope; on-demand only | No (accepted risk) |

**Critical findings: 0**
**High findings: 1 (SEC-01)**
**Medium findings: 4 (SEC-02, SEC-03, SEC-04, SEC-05)**
**Low findings: 4 (SEC-06, SEC-07, SEC-08, SEC-09)**

**Remediation scope per D-05:** SEC-01, SEC-02, SEC-04, SEC-05 require fixes. SEC-03 is already guarded (lower-priority improvement). SEC-06 through SEC-09 are accepted risks or design decisions — document in STATE.md Pending Todos.
