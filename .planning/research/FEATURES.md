# Feature Landscape

**Domain:** AI-augmented Personal Knowledge Management (Second Brain)
**Researched:** 2026-03-14
**Confidence:** MEDIUM — based on training data (cut-off Aug 2025) covering Obsidian, Notion AI, Mem, Roam, Logseq; no live web verification possible in this session. Core PKM feature landscape is stable.

---

## Table Stakes

Features users expect from any PKM system. Missing = system feels broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Markdown note creation | Every serious PKM stores in plain text; git-diffable, portable | Low | Already in scope — `~/SecondBrain/*.md` |
| YAML frontmatter metadata | Standard for machine-readable note properties (date, tags, type, links) | Low | Already in scope |
| Full-text search | Core utility — if you can't find it, you don't have it | Medium | SQLite FTS5 covers this |
| Backlinks / bidirectional links | Obsidian made this the industry norm; users expect to see "what links here" | Medium | `sb-link` command planned; needs UI surface too |
| Note templates | Repeatable structures for meetings, 1:1s, people profiles | Low | `.meta/templates/` folder; minimal engine work |
| Tagging / categorization | Rough organization without rigid hierarchy | Low | YAML frontmatter `tags:` field; search filters |
| Hierarchical folder structure | Even flat-first users want some folders (people/ meetings/ strategy/) | Low | Already designed into `~/SecondBrain/` layout |
| Note creation timestamp + last modified | Users reference when something was captured | Low | OS mtime + YAML frontmatter `created:` |
| Search by date range | "What did I note about X last month?" | Medium | SQLite query; needs CLI surface |
| Note linking (wikilinks or explicit) | Connect notes manually | Low | `[[note-title]]` wikilink convention is standard |
| Rebuild/reindex from source | If index is lost, system recovers | Medium | `/sb-reindex` already in scope as critical requirement |

---

## Differentiators

Features that set this system apart. Not universally expected, but high personal leverage for this owner (Operations Manager, Team Lead, Account Manager, Developer).

### AI Capture & Proactive Questioning

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Proactive AI questioning on capture | AI extracts context the user didn't explicitly write — the "cybernetic" core | High | Distinguishes from passive note tools; `sb-capture` triggers this |
| AI-inferred backlinks | AI suggests "this note mentions Alice — link to people/alice.md?" | High | Reduces manual link maintenance |
| Git commit auto-capture | Every code commit becomes a knowledge event linked to projects/people | Medium | Git hook already in scope; AI summarizes diff in plain language |
| File-drop categorization | Drop a PDF → AI asks: "Is this for project X or client Y?" | High | File watcher in scope; parsing complexity is moderate |
| Context-sensitive capture routing | Capture to the right folder automatically based on content classification | Medium | Requires local classifier (must not call cloud for PII routing decision) |

### Manager / Leader Persona Features

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-person profile notes | Single source of truth per report/stakeholder: role, history, growth themes | Low | `people/` folder; template drives consistency |
| 1:1 meeting notes linked to person | Every 1:1 auto-links to `people/<name>.md`; history accumulates over time | Medium | Bidirectional link: `meetings/` ↔ `people/` |
| Growth discussion log | Dedicated section in person profile for performance/growth; PII-routed to local model | Medium | Content-type routing is the complexity, not the note itself |
| "What do I know about X?" query | Ask about a person or project and get a synthesized summary | High | Requires AI + full context of person's notes; high leverage |
| OKR / initiative tracking in `strategy/` | Structure for quarterly goals, initiatives, key results | Low | Mainly a template problem; linking to projects is the harder part |
| Meeting → Action item extraction | AI reads meeting note, extracts tasks with owners | High | Post-capture AI pass; high manager leverage |
| Pre-meeting brief | "I have a 1:1 with Alice in 10 min — surface relevant context" | High | Requires temporal awareness + person context aggregation |

### CLI-First Features

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `sb-capture` with interactive prompting | Single command to capture anything; AI asks follow-ups inline | Medium | Core workflow; must be fast (<3s to first prompt) |
| `sb-search` with fuzzy/FTS query | Search from terminal without leaving workflow | Medium | SQLite FTS5; output as plain text or JSON |
| `sb-link` to manually connect notes | Explicitly link two notes from CLI | Low | Writes wikilink into frontmatter or note body |
| `sb-forget <person>` | GDPR erasure from CLI — deletes all notes + index records for a person | Medium | Already in scope; critical for compliance |
| `sb-check-links` | Find broken/orphaned links | Low | Consistency utility; prevents silent data rot |
| Claude Code subagent (`second-brain`) | Invoke brain from any Claude session without switching contexts | High | Highest leverage for developer/manager hybrid persona |
| `sb-init` bootstraps fresh install | One command from clone to working system | Low | Already in scope |

### Privacy & Compliance Differentiators

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| PII routing to local model | Growth notes never leave machine; no GDPR risk | High | Classification must be local (critical constraint) |
| Audit trail (created/accessed/modified) | Every note event logged in SQLite | Low | Compliance + personal review value |
| `sb-forget` right to erasure | Full deletion: markdown + SQLite index + audit trail | Medium | Already in scope |
| Local-first / offline operation | System works without internet | Low | Architecture already ensures this |

---

## Anti-Features

Features to explicitly NOT build in v1 — with rationale.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| GUI / web interface | Adds frontend complexity, build tooling, and auth surface; no user value until CLI is solid | CLI + Claude Cowork; GUI is an explicit future milestone |
| Calendar sync (Google Calendar / Outlook) | OAuth complexity, token refresh, API rate limits — a whole integration project | Manual meeting note capture via `sb-capture`; date in frontmatter |
| Mobile app / mobile access | DevContainer is desktop-only; mobile PKM is a different UX problem | Out of scope per PROJECT.md |
| Team / shared brain | Multi-user adds conflict resolution, access control, identity — entirely different system | Single-user only; design for extensibility not implementation |
| Plugin system / extensibility framework | Premature abstraction; not enough features to know what the extension points are | Hardcode first; extract patterns in v2 |
| Real-time sync / live collaboration | Contradicts local-first; Drive sync is already the sync layer | Drive handles sync; don't duplicate |
| Hierarchical tag taxonomy | Over-organization leads to tag bloat and maintenance burden | Flat tags + search; let AI surface connections |
| Automatic deduplication | Too many false positives; destroys notes | Suggest duplicates on capture; human decides |
| Notion-style databases / tables in notes | Rich data entry is a separate UX; conflicts with plain Markdown philosophy | Use YAML frontmatter for structured fields |
| Spaced repetition / flashcards | Valid PKM feature but different use case (learning retention vs working knowledge) | Not the persona need; out of scope |
| Web clipper / browser extension | Useful but not CLI-first; adds browser dependency | Copy-paste + `sb-capture` for now |
| Automatic meeting transcription | Microphone access, storage, privacy concerns | Manual notes; paste transcript if available |

---

## Feature Dependencies

```
sb-init
  → folder structure exists
  → templates installed

sb-capture
  → sb-init (folder structure)
  → AI proactive questioning (requires API configured)
  → content-type classifier (must be local, before routing decision)
  → PII routing → model router → Ollama (local) or Claude (cloud)

sb-search
  → SQLite index populated
  → sb-reindex (if index lost)

Backlinks / sb-link
  → Notes exist (sb-capture done)
  → AI-inferred links → sb-capture (runs at capture time)

1:1 notes → People profiles
  → people/<name>.md exists
  → meetings/<date>-<name>.md links to it (bidirectional)

"What do I know about X?" query
  → sb-search (base query)
  → AI synthesis (requires all person notes in context)
  → People profiles (source data)

Git hook auto-capture
  → sb-capture working
  → git installed in devcontainer
  → project folder recognized

sb-forget <person>
  → SQLite audit trail (to find all records)
  → people/<name>.md + all linked meetings
  → Index erasure

Pre-meeting brief
  → People profiles populated (history)
  → Meeting notes exist (context)
  → AI synthesis ("What do I know about X?")
```

---

## MVP Recommendation

The minimum that makes the system feel like a "brain" rather than a file system:

**Prioritize (v1 core):**
1. `sb-init` — bootstraps folder structure and templates
2. `sb-capture` with AI proactive questioning — the "cybernetic" differentiator
3. `sb-search` via SQLite FTS5 — find what you captured
4. People profile template + 1:1 note template — manager persona value from day 1
5. `sb-forget` — GDPR compliance is non-negotiable given PII in people notes
6. `sb-reindex` — data safety; must exist before real data is stored
7. Git hook capture — coding workflow integration, zero-friction

**Defer (post-v1):**
- `sb-check-links` — useful but not critical to core function
- Pre-meeting brief — depends on accumulated people history; little value on day 1
- Action item extraction from meetings — complex AI pass; validate capture first
- AI-inferred backlinks — optimize after manual linking patterns are understood
- Claude Code subagent — high value but can be added after core CLI works

---

## Persona-Specific Notes

Tuomas is an Operations Manager, Team Lead, and Developer simultaneously. This creates specific feature priority shifts vs. a generic PKM user:

- **People notes are critical infrastructure**, not a nice-to-have. Every 1:1, growth conversation, and performance discussion needs to be connected and findable — with GDPR safety.
- **Context switching is the enemy.** CLI-first matters because switching to a separate app breaks coding/writing flow. `sb-capture` must be invokable from terminal in <3 seconds.
- **Meeting prep is high-leverage.** "What do I know about this person or project before this meeting?" is a daily need. This becomes a killer feature once enough notes exist.
- **Git-to-knowledge flow** is unique to the developer-manager persona. Auto-summarizing commits and linking them to projects closes the loop between doing and documenting.

---

## Sources

- Training data knowledge of Obsidian (v1.x), Notion AI, Mem.ai, Roam Research, Logseq — MEDIUM confidence (stable features, no live verification)
- PROJECT.md (`/Users/tuomasleppanen/second-brain/.planning/PROJECT.md`) — HIGH confidence (primary context)
- Note: WebSearch was unavailable in this session; live competitor feature verification was not performed. Flag for manual validation if currency is critical.
