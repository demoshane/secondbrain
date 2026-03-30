# Phase 44: AI Provider Settings — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 44-ai-provider-settings
**Areas discussed:** Groq adapter scope, All-local toggle semantics, API key UX, Fallback on Groq failure

---

## Groq Adapter Scope

| Option | Description | Selected |
|--------|-------------|----------|
| ask_brain only | Only Ask Brain routes to Groq | |
| All public-sensitivity calls | Any sensitivity='public' call routes to Groq | |
| Configurable per call-type | Feature-group toggles in Settings | ✓ |

**Follow-up — granularity:**

| Option | Description | Selected |
|--------|-------------|----------|
| Toggle per feature group | One toggle each for Ask Brain, Follow-up questions, Digest, Person synthesis | ✓ |
| Groq replaces routing table | Extend existing routing dropdowns with 'groq' option | |

**User's choice:** Per-feature-group toggles stored in config.toml [groq]. Groups: ask_brain, followup_questions, digest, person_synthesis.

---

## All-Local Toggle Semantics

**Precedence when both Groq key + all-local active:**

| Option | Description | Selected |
|--------|-------------|----------|
| All-local always wins | Toggle is a hard privacy gate | ✓ |
| Groq key wins for public | All-local only applies to PII/private | |

**PII content:**

| Option | Description | Selected |
|--------|-------------|----------|
| PII always stays local regardless | Existing rule unchanged | ✓ |
| All-local toggle also controls PII | Redundant but explicit | |

**Toggle state storage:**

| Option | Description | Selected |
|--------|-------------|----------|
| config.toml [routing] all_local | Fits existing config pattern | ✓ |
| Separate toggle in Keychain | Unusual for a feature flag | |

**User note on storage:** "Settings page" — confirmed as config.toml, exposed in Settings UI.

**Local model:**

| Option | Description | Selected |
|--------|-------------|----------|
| llama3 (8B) as new default | Switch from llama3.2 (3B) per roadmap | ✓ |
| Keep llama3.2, let user configure | No silent change | |

---

## API Key UX

**Key field appearance once saved:**

| Option | Description | Selected |
|--------|-------------|----------|
| ✓ Configured — [Remove] button | No key value visible; Remove to rotate | ✓ |
| Password field, always enterable | Empty on load, re-enter to rotate | |
| Masked placeholder + Re-enter link | Bullet placeholder, Update key link | |

**Connectivity status:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — test ping on key entry | Auto-call POST /config/groq/test after save | ✓ |
| No — just show configured/not | No API call in Settings | |

---

## Fallback on Groq Failure

**Runtime failure behaviour:**

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to claude subprocess | Reuse FallbackAdapter pattern | ✓ |
| Fall back to local Ollama | Stays fully local on failure | |
| Surface error to user | No silent fallback | |

**User notification:**

| Option | Description | Selected |
|--------|-------------|----------|
| Silent fallback | Transparent to user | |
| Show a subtle warning | Toast: "Groq unavailable, used fallback model" | ✓ |

---

## Claude's Discretion

- Exact Tailwind classes for new Settings section
- httpx vs requests for Groq HTTP adapter
- Auto-test on save vs separate Test button (recommended: auto)
- FallbackAdapter signalling mechanism for fallback detection

## Deferred Ideas

None.
