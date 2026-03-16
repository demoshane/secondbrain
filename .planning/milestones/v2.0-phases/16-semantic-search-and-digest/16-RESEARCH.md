# Phase 16: Semantic Search and Digest — Research

**Researched:** 2026-03-15
**Domain:** Vector/hybrid search (sqlite-vec + FTS5 RRF), cross-context entity recap, weekly digest generation, launchd scheduling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Hybrid search output**
- Default `sb-search` (no flags) = hybrid BM25 + vector via RRF; output looks identical to today (ranked list, no source indicator or score shown)
- `--keyword` flag for pure BM25 bypass (exact/literal match use case)
- `--semantic` flag retained for pure vector-only queries
- Default result limit: 20 (no change from current FTS5 default)
- Three modes: `sb-search` (hybrid), `sb-search --semantic` (pure vector), `sb-search --keyword` (pure BM25)

**sb-recap <name> scope**
- Works for both people AND projects/topics (unified command, any entity name)
- Source notes: full-brain search — all notes mentioning the name via FTS + semantic match
- Context window: top 20 most semantically relevant notes
- Output structure: narrative summary + open action items (prose + bullet actions)
- PII routing: Ollama for PII, Claude for non-PII (per SRCH-04)

**Digest content and format**
- Trigger: both automatic (launchd weekly) AND on-demand (`sb-digest` command)
- Sections: Key Themes, Open Actions, Stale Notes, Captures This Week
- Format: Structured Markdown with YAML frontmatter (`title`, `date`, `type: digest`)
- File naming: `YYYY-WNN.md` (e.g. `2026-W11.md`) in `.meta/digests/`
- Readable via: `sb-read --digest latest`
- PII summaries via Ollama, non-PII via Claude

**Semantic fallback**
- Missing embeddings at query time: generate on the fly (up to 50 notes); if >50 unembed, warn and suggest `sb-reindex`
- No embeddings in DB at all: hybrid silently falls back to pure FTS5 + shows notification: "Semantic unavailable. Run sb-reindex to enable."
- `sb-recap <name>` entity not found: graceful empty state — "No notes found about 'alice'. Capture a meeting or note to build context."

### Claude's Discretion
- RRF fusion weights (BM25 vs vector score balance)
- launchd schedule day/time for weekly digest (e.g. Monday 08:00)
- Exact wording of Key Themes synthesis prompt
- `sb-digest` CLI verb and flag design

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRCH-01 | User can run `sb-search --semantic` for vector-enhanced search | sqlite-vec cosine KNN query pattern documented below; embed_texts() already handles on-the-fly generation |
| SRCH-02 | Hybrid search merges BM25 and vector results via Reciprocal Rank Fusion | RRF formula `1/(k+rank)` is well-established; both FTS5 ranks and vec distances available; no third-party fusion library needed |
| SRCH-03 | User can run `sb-recap <name>` for cross-context synthesis across all notes about a person or project | Extends existing recap_main(); FTS + vector fetch pattern documented; PII routing via existing _RouterShim |
| SRCH-04 | Cross-context synthesis routes PII notes through Ollama only | Existing `router.get_adapter(sensitivity, CONFIG_PATH)` pattern directly reusable; sensitivity comes from notes.sensitivity column |
| DIAG-01 | Weekly digest is generated automatically and saved to `.meta/digests/` | launchd plist pattern exists in install_native.py; `StartCalendarInterval` dict with Weekday/Hour/Minute keys |
| DIAG-02 | Digest includes: notes captured this week, key themes, open actions, stale items | All data available in DB: notes.created_at, action_items, intelligence.get_stale_notes(); themes require AI synthesis |
| DIAG-03 | User can read the latest digest via `sb-read --digest latest` | `sb-read` main() already has argparse; add `--digest` flag that resolves path via glob sort on `.meta/digests/` |
| DIAG-04 | Digest generation routes PII note summaries through Ollama | Same `get_adapter(sensitivity)` per-note pattern; aggregate digest text uses Claude for non-PII sections |
</phase_requirements>

---

## Summary

Phase 16 adds three capabilities on top of the embedding infrastructure built in Phase 14: (1) semantic and hybrid search modes to `sb-search`, (2) a `sb-recap <name>` cross-entity synthesis command, and (3) automated weekly digest generation via `sb-digest` and launchd. All three rely on the `note_embeddings` table and `sqlite-vec` extension that already exist in the schema. No new external libraries are required — the full stack (`sqlite-vec`, `engine.embeddings`, `engine.router`, FTS5) is already installed and tested.

The most technically novel piece is Reciprocal Rank Fusion (RRF). RRF is a simple formula — `1 / (k + rank)` summed per candidate across ranked lists — that requires no additional dependencies. The key implementation detail is that BM25 scores are negative (more negative = better match) while vector cosine distances are positive (lower = closer); both must be converted to ranks before fusion. The `note_embeddings` table stores blobs compatible with `vec_distance_cosine()` from sqlite-vec, which is the same pattern already used in `find_similar()` in intelligence.py.

The digest and recap features both use the established `_RouterShim` / `get_adapter(sensitivity, CONFIG_PATH)` pattern from Phase 15 for PII routing. The digest file format (YAML frontmatter + Markdown sections) follows the same pattern as all other notes, meaning `frontmatter` library handles both reading and writing. The weekly launchd trigger follows the same `plistlib.dump()` approach already in `scripts/install_native.py`, using `StartCalendarInterval` for calendar-based scheduling.

**Primary recommendation:** Implement in four sequential tasks: (1) semantic vector search function + `--semantic` flag, (2) RRF hybrid merge + `--keyword` flag + fallback logic, (3) `recap_entity()` + extended `sb-recap <name>` CLI, (4) digest engine + `sb-digest` CLI + `--digest` flag on `sb-read` + launchd plist.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite-vec | >=0.1 (already in pyproject.toml) | KNN vector search via `vec_distance_cosine()` | Already installed; used in `find_similar()` in intelligence.py |
| python-frontmatter | >=1.0 (already installed) | Parse/write YAML frontmatter + Markdown body | Used throughout codebase for all note I/O |
| plistlib | stdlib | Write launchd plist for digest job | Already used in `scripts/install_native.py` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime / isoformat | stdlib | ISO week number (`%G-W%V`) for digest filename | Week-of-year calculation for YYYY-WNN format |
| engine.embeddings.embed_texts | project | On-the-fly query embedding | Every semantic search invocation |
| engine.router.get_adapter | project | PII routing for recap + digest synthesis | Any AI generation call on note content |
| engine.intelligence.get_stale_notes | project | Stale items section of digest | Reuse existing logic, no reimplementation |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled RRF | `rank_bm25` + `faiss` | Way more complexity; RRF formula is 3 lines of Python |
| plistlib digest plist | Separate cron job | cron requires PATH hacks; launchd is macOS-native and already established |
| `StartCalendarInterval` | `StartInterval` (seconds) | Calendar interval fires at a specific weekday/time; interval fires every N seconds regardless — calendar is correct for weekly digest |

**Installation:** No new packages needed. All dependencies are already in `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

New files this phase:

```
engine/
├── search.py          # EXTEND: add search_semantic(), search_hybrid(), update main()
├── intelligence.py    # EXTEND: add recap_entity(), entity synthesis prompts
└── digest.py          # NEW: generate_digest(), digest_main() (sb-digest entry point)

scripts/
└── install_native.py  # EXTEND: add write_digest_plist(), install digest launchd agent

tests/
├── test_search.py     # EXTEND: new test classes for semantic + hybrid modes
├── test_intelligence.py # EXTEND: TestRecapEntity class
└── test_digest.py     # NEW: digest generation and file output tests
```

### Pattern 1: sqlite-vec KNN Query

**What:** Load sqlite-vec extension, embed query text, run `vec_distance_cosine` ORDER BY LIMIT query against `note_embeddings`.

**When to use:** `sb-search --semantic` and as the vector leg of hybrid search.

```python
# Source: engine/intelligence.py find_similar() — established pattern
import sqlite_vec
conn.enable_load_extension(True)
sqlite_vec.load(conn)

query_blob = embed_texts([query_text], provider=provider)[0]

rows = conn.execute(
    """
    SELECT ne.note_path, n.title, n.type, n.created_at, n.sensitivity,
           vec_distance_cosine(ne.embedding, ?) AS dist
    FROM note_embeddings ne
    JOIN notes n ON ne.note_path = n.path
    ORDER BY dist
    LIMIT ?
    """,
    (query_blob, limit),
).fetchall()
# similarity = 1.0 - dist
```

**Confidence: HIGH** — directly derived from working `find_similar()` in intelligence.py.

### Pattern 2: Reciprocal Rank Fusion

**What:** Merge two ranked lists (BM25 results and vector results) using RRF formula.

**When to use:** Default `sb-search` (hybrid mode).

```python
# RRF standard k=60 (well-established default in information retrieval literature)
def _rrf_merge(
    bm25_results: list[dict],      # ordered best-first (most-negative score first)
    vec_results: list[dict],       # ordered best-first (lowest dist first)
    k: int = 60,
    limit: int = 20,
) -> list[dict]:
    scores: dict[str, float] = {}
    all_items: dict[str, dict] = {}

    for rank, item in enumerate(bm25_results):
        path = item["path"]
        scores[path] = scores.get(path, 0.0) + 1.0 / (k + rank + 1)
        all_items[path] = item

    for rank, item in enumerate(vec_results):
        path = item["path"]  # vec results use "note_path" key — normalise on build
        scores[path] = scores.get(path, 0.0) + 1.0 / (k + rank + 1)
        all_items[path] = item

    merged = sorted(scores.keys(), key=lambda p: scores[p], reverse=True)
    return [all_items[p] for p in merged[:limit]]
```

**Confidence: HIGH** — RRF formula is standard; k=60 is the canonical default from the original Cormack et al. paper.

### Pattern 3: PII-Aware Batch Summarisation (Digest + Recap)

**What:** For each note contributing to digest/recap, route its content through the correct adapter based on `sensitivity` column.

**When to use:** Digest "Key Themes" section, `sb-recap <name>` synthesis.

```python
# Follows established engine/intelligence.py _RouterShim pattern
from engine.paths import CONFIG_PATH

pii_texts = []
public_texts = []

for row in note_rows:
    if row["sensitivity"] == "pii":
        pii_texts.append(row["body"][:500])   # truncate for context window
    else:
        public_texts.append(row["body"][:500])

# Summarise PII notes via Ollama
if pii_texts:
    adapter = _router.get_adapter("pii", CONFIG_PATH)
    pii_summary = adapter.generate(user_content="\n\n".join(pii_texts),
                                   system_prompt=SUMMARY_SYSTEM_PROMPT)

# Summarise non-PII notes via Claude
if public_texts:
    adapter = _router.get_adapter("public", CONFIG_PATH)
    public_summary = adapter.generate(user_content="\n\n".join(public_texts),
                                      system_prompt=SUMMARY_SYSTEM_PROMPT)
```

**Confidence: HIGH** — direct reuse of established pattern from intelligence.py.

### Pattern 4: Digest File Writing

**What:** Write YAML frontmatter + Markdown sections to `.meta/digests/YYYY-WNN.md`.

**When to use:** Both `sb-digest` on-demand and launchd weekly trigger.

```python
import datetime
import frontmatter  # python-frontmatter

def _week_filename() -> str:
    """Return ISO week filename like '2026-W11.md'."""
    today = datetime.date.today()
    # %G = ISO year, %V = ISO week number (zero-padded)
    return today.strftime("%G-W%V") + ".md"

def write_digest(content: dict, digests_dir: Path) -> Path:
    digests_dir.mkdir(parents=True, exist_ok=True)
    filename = _week_filename()
    out_path = digests_dir / filename

    post = frontmatter.Post(
        content=_render_digest_body(content),
        title=f"Weekly Digest {filename[:-3]}",
        date=datetime.date.today().isoformat(),
        type="digest",
    )
    out_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return out_path
```

**Confidence: HIGH** — `frontmatter.Post` + `frontmatter.dumps()` is the standard write pattern used elsewhere in codebase.

### Pattern 5: launchd Calendar Scheduling

**What:** Add a second plist alongside `com.secondbrain.watch` that fires `sb-digest` weekly.

**When to use:** DIAG-01 automatic weekly trigger.

```python
# Source: scripts/install_native.py write_plist() pattern
DIGEST_PLIST_LABEL = "com.secondbrain.digest"

plist = {
    "Label": DIGEST_PLIST_LABEL,
    "ProgramArguments": [str(sb_digest_bin)],
    "WorkingDirectory": str(Path.home() / "SecondBrain"),
    "EnvironmentVariables": {
        "PATH": f"{Path.home()}/.local/bin:/usr/local/bin:/usr/bin:/bin",
        "HOME": str(Path.home()),
    },
    # Monday 08:00 local time
    "StartCalendarInterval": {"Weekday": 1, "Hour": 8, "Minute": 0},
    "StandardOutPath": str(log_dir / "second-brain-digest.log"),
    "StandardErrorPath": str(log_dir / "second-brain-digest-error.log"),
}
```

**launchd Weekday values:** 0=Sunday, 1=Monday, 2=Tuesday ... 7=Sunday (both 0 and 7 = Sunday).

**Confidence: HIGH** — `StartCalendarInterval` is a macOS launchd standard key; `plistlib.dump()` pattern taken directly from existing `write_plist()`.

### Pattern 6: `sb-read --digest latest` resolution

**What:** Resolve "latest" to the most recent file in `.meta/digests/` by filename sort (ISO week filenames sort lexicographically in chronological order).

**When to use:** `sb-read --digest latest` (DIAG-03).

```python
# In engine/read.py main() — add --digest flag
def _resolve_digest(digests_dir: Path, selector: str) -> Path | None:
    files = sorted(digests_dir.glob("*.md"))
    if not files:
        return None
    if selector == "latest":
        return files[-1]   # lexicographic sort of YYYY-WNN is chronological
    # Could also accept explicit week like "2026-W11"
    target = digests_dir / f"{selector}.md"
    return target if target.exists() else None
```

### Pattern 7: On-the-fly Embedding at Query Time

**What:** When a search query arrives and some notes have no embeddings, embed them inline before running the vector query.

**When to use:** Fallback for SRCH-01/SRCH-02 when some notes lack embeddings.

```python
def _ensure_query_embeddings(conn, provider: str, limit: int = 50) -> int:
    """Embed up to `limit` unembed notes inline. Returns count of notes still missing."""
    missing = conn.execute(
        """SELECT n.path, n.body FROM notes n
           LEFT JOIN note_embeddings ne ON ne.note_path = n.path
           WHERE ne.note_path IS NULL"""
    ).fetchall()
    if not missing:
        return 0
    if len(missing) > limit:
        return len(missing)  # caller decides whether to warn
    # Reuse embed_pass with the unembed subset
    from engine.embeddings import embed_texts
    # ... batch embed and upsert (same upsert SQL as reindex.embed_pass)
    return 0
```

### Anti-Patterns to Avoid

- **Loading sqlite-vec twice:** `enable_load_extension(True)` + `sqlite_vec.load(conn)` must be called once per connection. Wrap in a helper `_load_vec(conn)` called at the top of each search function that needs it, guarded by a try/except for environments without sqlite-vec.
- **Normalising scores instead of ranks before RRF:** RRF works on rank positions, not raw scores. BM25 scores are negative floats and vector distances are positive floats — neither should be normalised; just convert the ordered list position to rank.
- **Blocking digest on AI failure:** Digest generation must be best-effort. If the AI synthesis step fails (Ollama down, Claude rate-limit), write the digest with the mechanical sections (Captures This Week, Open Actions, Stale Notes) and substitute a fallback message for Key Themes. Never skip writing the file.
- **Writing digest on every run if already exists for this week:** Check if `_week_filename()` already exists before generating. If it does, `sb-digest` should print "Digest for this week already exists: <path>" and exit 0 (idempotent).
- **Using `sb-read`'s PII passphrase gate for digest files:** Digest files have `type: digest` not `content_sensitivity: pii`. They may contain summaries of PII content but the digest file itself is not classified as PII — access control is out of scope for this phase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vector similarity search | Custom cosine similarity in Python | `vec_distance_cosine()` via sqlite-vec | Already installed; C extension; handles BLOB format already used in `note_embeddings` |
| Rank fusion maths library | Custom weighted normalisation | Hand-coded RRF (`1/(k+rank)`) — it's 10 lines | RRF needs no library; simpler and more robust than score normalisation |
| PII routing | Custom sensitivity check | `engine.router.get_adapter(sensitivity, CONFIG_PATH)` | Already handles pii/private/public routing; tested; GDPR-compliant |
| Stale note detection | Re-implement staleness logic | `engine.intelligence.get_stale_notes(conn)` | Already implements 90-day window, evergreen exclusion, snooze |
| Frontmatter parse/write | String templating for digest | `python-frontmatter` (`frontmatter.Post`, `frontmatter.dumps`) | Already used for all note I/O; handles edge cases in YAML |
| ISO week number | `(date - epoch).days // 7` | `date.strftime("%G-W%V")` | `%G-W%V` is the correct ISO 8601 week format; handles year-boundary weeks correctly |
| launchd XML | Manual XML string construction | `plistlib.dump()` | Already used in `install_native.py`; stdlib; correct binary/XML plist format |

---

## Common Pitfalls

### Pitfall 1: BM25 Scores Are Negative — Can't Rank Mix Directly

**What goes wrong:** `bm25(notes_fts)` returns negative floats (e.g. -3.2 = good match, -0.1 = weak). Treating these as positive magnitudes or trying to compare them directly with vector distances (positive, 0–2 range) produces nonsense rankings.
**Why it happens:** SQLite FTS5 BM25 returns negative scores by convention so that `ORDER BY bm25(...)` sorts best-first.
**How to avoid:** In `_rrf_merge`, enumerate each list in best-first order and use the index as rank. Never mix raw score values across the two lists.
**Warning signs:** Hybrid results return weak keyword matches ranked above strong semantic matches.

### Pitfall 2: sqlite-vec Extension Not Loaded Per-Connection

**What goes wrong:** `OperationalError: no such function: vec_distance_cosine` even though sqlite-vec is installed.
**Why it happens:** SQLite extensions are per-connection state. `enable_load_extension(True)` + `sqlite_vec.load(conn)` must be called on the specific connection object being used.
**How to avoid:** Create a `_load_vec(conn)` helper at the top of `search.py` (mirrors the pattern in `find_similar()` in intelligence.py). Call it at the start of any function that runs vec queries.
**Warning signs:** Works in isolation but fails when connection is opened by `get_connection()` without the extension load sequence.

### Pitfall 3: ISO Week Year vs Calendar Year Mismatch

**What goes wrong:** Digest file for week 1 of 2027 is named `2026-W01.md` instead of `2027-W01.md`.
**Why it happens:** `%Y` is the Gregorian calendar year; `%G` is the ISO week year. The last days of December can belong to week 1 of the next ISO year.
**How to avoid:** Always use `strftime("%G-W%V")` — `%G` (ISO year) paired with `%V` (ISO week).
**Warning signs:** Files created in late December have wrong year prefix.

### Pitfall 4: recap_entity() Context Window Overflow

**What goes wrong:** Passing 20 full note bodies to the AI adapter exceeds context window or produces unusably long synthesis.
**Why it happens:** Notes can be hundreds to thousands of tokens each; 20 full bodies can be 30k+ tokens.
**How to avoid:** Truncate each note body to 500 characters before passing to synthesis prompt. The top-level summary structure (narrative + action items) should still be generated from truncated snippets — enough for theme extraction.
**Warning signs:** AI adapter returns errors about context length, or synthesis takes >30 seconds.

### Pitfall 5: Digest Written to Wrong Directory

**What goes wrong:** Digest files appear in the repo `.meta/` directory instead of `~/SecondBrain/.meta/digests/`.
**Why it happens:** `engine.paths.BRAIN_ROOT` resolves relative to `cwd`, which differs between launchd job (WorkingDirectory = ~/SecondBrain) and local dev (repo root).
**How to avoid:** Always derive `digests_dir` from `BRAIN_ROOT / ".meta" / "digests"` where `BRAIN_ROOT` is resolved from `engine.paths` (which reads from config, not cwd). In tests, patch `engine.paths.BRAIN_ROOT` to a tmp_path.
**Warning signs:** `sb-digest` in dev creates `.meta/digests/` inside the repo.

### Pitfall 6: `--digest latest` Fails on Empty Directory

**What goes wrong:** `IndexError` when `sorted(digests_dir.glob("*.md"))` returns empty list and code does `files[-1]`.
**Why it happens:** First-run: no digests have been generated yet.
**How to avoid:** Check `if not files: print("No digests found."); return 0` before indexing.

---

## Code Examples

### Full hybrid_search() skeleton

```python
# engine/search.py — new function
def search_hybrid(
    conn: sqlite3.Connection,
    query: str,
    limit: int = 20,
    k: int = 60,
) -> list[dict]:
    """Hybrid BM25 + vector search via Reciprocal Rank Fusion."""
    # 1. FTS5 leg — fetch 2x limit for re-ranking headroom
    bm25 = search_notes(conn, query, limit=limit * 2)

    # 2. Vector leg
    try:
        import sqlite_vec
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
    except Exception:
        return bm25[:limit]  # fallback: no sqlite-vec

    from engine.embeddings import embed_texts
    from engine.config_loader import load_config
    from engine.paths import CONFIG_PATH
    cfg = load_config(CONFIG_PATH)
    provider = cfg.get("embeddings", {}).get("provider", "ollama")

    # Check embeddings exist
    count = conn.execute("SELECT COUNT(*) FROM note_embeddings").fetchone()[0]
    if count == 0:
        print("Semantic unavailable. Run sb-reindex to enable.")
        return bm25[:limit]

    query_blob = embed_texts([query], provider=provider)[0]
    vec_rows = conn.execute(
        """SELECT ne.note_path AS path, n.type, n.title, n.created_at,
                  vec_distance_cosine(ne.embedding, ?) AS dist
           FROM note_embeddings ne
           JOIN notes n ON ne.note_path = n.path
           ORDER BY dist LIMIT ?""",
        (query_blob, limit * 2),
    ).fetchall()
    vec_results = [
        {"path": r[0], "type": r[1], "title": r[2], "created_at": r[3], "score": 1.0 - r[4]}
        for r in vec_rows
    ]

    # 3. RRF merge
    return _rrf_merge(bm25, vec_results, k=k, limit=limit)
```

### Digest body renderer

```python
# engine/digest.py
DIGEST_BODY_TEMPLATE = """\
## Key Themes

{key_themes}

## Open Actions

{open_actions}

## Stale Notes

{stale_notes}

## Captures This Week

{captures}
"""
```

### Week filename

```python
import datetime
def week_filename() -> str:
    return datetime.date.today().strftime("%G-W%V") + ".md"
# e.g. "2026-W11.md"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure FTS5 keyword search | Hybrid RRF (BM25 + cosine) | Phase 16 | Semantic relevance without keyword overlap |
| `sb-recap` = session recap only | `sb-recap <name>` = any entity | Phase 16 | Generalised to people, projects, topics |
| No digest | Weekly automated + on-demand digest | Phase 16 | Surfaces themes and actions passively |
| `sb-read <path>` only | `sb-read --digest latest` | Phase 16 | Consistent CLI surface for digest content |

---

## Open Questions

1. **RRF weight symmetry (BM25 vs vector)**
   - What we know: Standard RRF treats both lists equally (each contributes `1/(k+rank)`)
   - What's unclear: Whether asymmetric weighting (e.g. 0.7 vector + 0.3 BM25) produces better results for this corpus
   - Recommendation: Start with equal weighting (k=60 for both). This is in Claude's discretion per CONTEXT.md. Symmetric is the safe default; can be tuned with a config key later if needed.

2. **`sb-digest` command: standalone CLI vs flag on `sb-reindex`**
   - What we know: CONTEXT.md says "sb-digest CLI verb" is at Claude's discretion
   - What's unclear: Whether to add `--digest` to `sb-reindex` or create a separate `sb-digest` entry point
   - Recommendation: Separate `engine/digest.py` with `digest_main()` registered as `sb-digest` in pyproject.toml. Keeps concerns separate from reindex; follows codebase pattern of one entry point per feature module.

3. **`sb-read --digest latest` vs separate `sb-digest --read`**
   - What we know: CONTEXT.md locks "readable via sb-read --digest latest"
   - What's unclear: Whether `read.py` should import `digest.py` or just resolve the path and delegate to existing `read_note()`
   - Recommendation: `sb-read --digest latest` resolves the path to the latest digest file, then calls `read_note(path, conn)` — no new read logic, just path resolution. Digest files are not PII-gated.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 7.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_search.py tests/test_intelligence.py tests/test_digest.py -q -x` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SRCH-01 | `--semantic` returns semantically similar note with no keyword overlap | unit | `pytest tests/test_search.py::TestSemanticSearch -x` | ❌ Wave 0 |
| SRCH-01 | Fallback when >50 unembed notes: warning printed, suggests sb-reindex | unit | `pytest tests/test_search.py::TestSemanticFallback -x` | ❌ Wave 0 |
| SRCH-02 | Hybrid RRF result list contains items from both BM25 and vector lists | unit | `pytest tests/test_search.py::TestHybridSearch -x` | ❌ Wave 0 |
| SRCH-02 | `--keyword` bypasses vector, returns pure BM25 results | unit | `pytest tests/test_search.py::TestKeywordFlag -x` | ❌ Wave 0 |
| SRCH-02 | No embeddings in DB: hybrid falls back to FTS5 + notification | unit | `pytest tests/test_search.py::TestHybridFallback -x` | ❌ Wave 0 |
| SRCH-03 | `recap_entity("alice")` returns prose + action bullets when PII notes present | unit | `pytest tests/test_intelligence.py::TestRecapEntity -x` | ❌ Wave 0 |
| SRCH-03 | `recap_entity("unknown")` prints empty state message | unit | `pytest tests/test_intelligence.py::TestRecapEntityEmpty -x` | ❌ Wave 0 |
| SRCH-04 | PII notes in recap sent to Ollama adapter, not Claude adapter | unit | `pytest tests/test_intelligence.py::TestRecapEntityPIIRouting -x` | ❌ Wave 0 |
| DIAG-01 | Digest file written to `.meta/digests/YYYY-WNN.md` | unit | `pytest tests/test_digest.py::TestDigestWrite -x` | ❌ Wave 0 |
| DIAG-01 | Digest is idempotent: second run same week does not overwrite | unit | `pytest tests/test_digest.py::TestDigestIdempotent -x` | ❌ Wave 0 |
| DIAG-02 | Digest body contains all four sections | unit | `pytest tests/test_digest.py::TestDigestSections -x` | ❌ Wave 0 |
| DIAG-03 | `sb-read --digest latest` resolves to most recent digest file | unit | `pytest tests/test_read.py::TestDigestFlag -x` | ❌ Wave 0 |
| DIAG-03 | `sb-read --digest latest` on empty dir prints "No digests found." | unit | `pytest tests/test_read.py::TestDigestFlagEmpty -x` | ❌ Wave 0 |
| DIAG-04 | PII note summaries in digest use Ollama adapter | unit | `pytest tests/test_digest.py::TestDigestPIIRouting -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_search.py tests/test_intelligence.py tests/test_digest.py -q -x`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_search.py` — add `TestSemanticSearch`, `TestSemanticFallback`, `TestHybridSearch`, `TestKeywordFlag`, `TestHybridFallback` classes (RED stubs)
- [ ] `tests/test_intelligence.py` — add `TestRecapEntity`, `TestRecapEntityEmpty`, `TestRecapEntityPIIRouting` classes (RED stubs)
- [ ] `tests/test_digest.py` — new file; covers `TestDigestWrite`, `TestDigestIdempotent`, `TestDigestSections`, `TestDigestPIIRouting`
- [ ] `tests/test_read.py` — add `TestDigestFlag`, `TestDigestFlagEmpty` classes
- [ ] `engine/digest.py` — new module (stub with `NotImplementedError` in Wave 0)
- [ ] `pyproject.toml` — register `sb-digest = "engine.digest:digest_main"` script entry point

No new framework install needed — pytest already present.

---

## Sources

### Primary (HIGH confidence)

- `engine/intelligence.py` `find_similar()` — authoritative sqlite-vec usage pattern in this codebase
- `engine/search.py` `search_notes()` — authoritative FTS5/BM25 pattern; score ordering convention confirmed
- `engine/reindex.py` `embed_pass()` — authoritative on-the-fly embedding upsert pattern
- `engine/router.py` `get_adapter()` — authoritative PII routing pattern
- `scripts/install_native.py` `write_plist()` — authoritative launchd plist pattern; `plistlib.dump()` usage confirmed
- `pyproject.toml` — confirmed installed deps: sqlite-vec >=0.1, python-frontmatter >=1.0; no new installs needed
- `engine/db.py` `SCHEMA_SQL` — confirmed `note_embeddings` table schema including BLOB column and `sensitivity` on `notes`

### Secondary (MEDIUM confidence)

- Cormack, Clarke, Buettcher (2009) "Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods" — k=60 default is from this paper; widely reproduced in search literature
- Python `datetime.strftime("%G-W%V")` — ISO 8601 week date format; verified against Python docs (stdlib, no version concern)
- launchd `StartCalendarInterval` `Weekday` key — macOS launchd.plist(5) man page; 0=Sunday, 1=Monday convention confirmed via Apple Developer Documentation

### Tertiary (LOW confidence)

- None — all findings are grounded in codebase inspection or stdlib/well-established algorithms.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already present in codebase and pyproject.toml; no new deps
- Architecture: HIGH — all patterns derived directly from existing working code in this repo
- Pitfalls: HIGH (BM25 sign, sqlite-vec per-connection, ISO week year) — confirmed from codebase analysis; MEDIUM (context overflow) — based on general LLM knowledge
- Validation architecture: HIGH — test framework confirmed; test class names follow existing pattern in test_intelligence.py

**Research date:** 2026-03-15
**Valid until:** 2026-06-15 (stable stack — sqlite-vec, frontmatter, launchd are all stable APIs)
