# Phase 3: AI Layer - Research

**Researched:** 2026-03-14
**Domain:** PII routing, Ollama adapter, Claude Code integration, adapter pattern, config-driven model mapping
**Confidence:** HIGH (core patterns) / MEDIUM (Claude Code subprocess integration)

---

<user_constraints>
## User Constraints

### Locked Decisions (from project memory + STATE.md)

- **No Anthropic SDK calls.** User is on Claude Max plan (no API key). The "Anthropic adapter" MUST route through Claude Code's built-in Claude access — `claude -p <prompt>` subprocess — NOT `anthropic.Anthropic(api_key=...)`.
- **PII classification is local-only.** Rules + `content_sensitivity` frontmatter field. No cloud API call is made before classification confirms non-PII. Classifier runs BEFORE any adapter is called.
- **ModelRouter is the GDPR enforcement point.** It must be built and tested before any feature calls an AI API.
- **Ollama endpoint is `http://host.docker.internal:11434`** from inside DevContainer (macOS Docker Desktop). Linux DevContainers need `--add-host=host.docker.internal:host-gateway` in devcontainer.json.
- **Adapter pattern in `engine/adapters/`.** New AI models (OpenAI, Gemini) added via new adapter file, not by modifying core.
- **Prompt injection protection.** Note content NEVER interpolated into system prompts; passed as quoted user content.

### Claude's Discretion

- Choice of local PII keyword list (what keywords trigger PII classification)
- Specific proactive questions per content type (questions are content-type-aware — exact wording is implementation detail)
- Whether Claude Code adapter uses `claude -p` CLI subprocess or another mechanism (research this — see Open Questions)
- Model names to default to in `config.toml` (e.g., which Ollama model for PII, which Claude model for non-PII)
- Error handling when Ollama is unreachable (degrade gracefully vs. hard fail)

### Deferred Ideas (OUT OF SCOPE for Phase 3)

- File watcher (CAP-04) — Phase 4
- Git commit hook AI summarisation (CAP-05) — Phase 4
- SEARCH-04 RAG-lite retrieval — Phase 4
- GDPR-01/02/04 forget/purge/access-control — Phase 5
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AI-01 | On every `/sb-capture` invocation, AI asks 2–3 proactive questions (content-type-aware) | `engine/ai.py` `ask_followup_questions(note_type, title, body)` → calls ModelRouter → adapter; questions defined per content type as system prompt fragments |
| AI-02 | PII classifier runs locally (keyword rules + `content_sensitivity` frontmatter) BEFORE any AI API call | `engine/classifier.py` — pure Python, no deps; checks frontmatter field first, then keyword scan of body; returns `"pii"/"private"/"public"` |
| AI-03 | Notes with `content_sensitivity: pii` routed to Ollama only | ModelRouter reads classifier result; dispatches to `OllamaAdapter`; never calls `ClaudeAdapter` for PII |
| AI-04 | Notes with `content_sensitivity: private` or `public` routed to Claude | ModelRouter dispatches to `ClaudeAdapter` (claude -p subprocess) |
| AI-05 | Per-content-type model routing configurable in `.meta/config.toml` without code changes | `tomllib` (stdlib, Python 3.11+) reads `config.toml`; ModelRouter consults config on every call (no restart needed — read file fresh each time) |
| AI-06 | Other AI models addable via adapter pattern in `engine/adapters/` without changing core logic | Abstract `BaseAdapter` with `generate(prompt, system) -> str`; `OllamaAdapter`, `ClaudeAdapter` implement it |
| AI-07 | `second-brain` Claude Code subagent installable and invokable from any Claude session | `.claude/agents/second-brain.md` with YAML frontmatter; install script copies to `~/.claude/agents/` |
| AI-08 | `/sb-capture` available as a Claude Code skill (`/sb-capture`) | `.claude/commands/sb-capture.md` (legacy) or `.claude/skills/sb-capture/SKILL.md` (preferred) |
| AI-09 | File watcher includes debounce (min 5s) and rate limiting | File watcher is Phase 4 — but debounce/rate-limit module should be designed as a standalone utility in Phase 3 to unblock Phase 4 |
| AI-10 | Prompt injection protection: note content never interpolated into system prompts | All adapters separate `system` (static) from `user` (note content) in message construction; verified by test |
| CAP-06 | AI automatically updates Claude memory (CLAUDE.md or memory files) when relevant project/people context is captured | `ClaudeAdapter` skill writes to `~/.claude/projects/.../memory/MEMORY.md` via `claude -p` with explicit Write tool |
</phase_requirements>

---

## Summary

Phase 3 adds an AI layer on top of the existing capture pipeline. The central piece is `ModelRouter` — a thin dispatcher that (1) reads the local PII classification, (2) consults a TOML config for model assignments, and (3) calls the appropriate adapter. Two adapters ship in Phase 3: `OllamaAdapter` (for PII content) and `ClaudeAdapter` (for non-PII content).

The hardest constraint is the Anthropic Max plan: there is no API key. The `ClaudeAdapter` cannot use the `anthropic` Python SDK. Instead it invokes `claude -p "<prompt>"` as a subprocess — the Claude Code CLI uses the user's authenticated Max plan session. This is a deliberate architectural choice, not a workaround: it means the adapter works exactly like the user's interactive Claude Code session and respects the same permissions. The `claude -p` flag runs non-interactively, prints the response, and exits — exactly what an adapter needs.

The PII classifier (`engine/classifier.py`) is the GDPR enforcement boundary. It runs entirely locally with no network calls. It checks the `content_sensitivity` frontmatter field first (explicit user declaration takes priority), then falls back to keyword scanning the note body. The classifier result is passed to the ModelRouter before any adapter is invoked.

The Claude Code subagent (AI-07) is a markdown file with YAML frontmatter stored in `.claude/agents/second-brain.md`. When installed to `~/.claude/agents/`, it is available in all Claude sessions. The `/sb-capture` skill (AI-08) is a `.claude/commands/sb-capture.md` file.

**Primary recommendation:** Build in this order — classifier → adapter base class → OllamaAdapter → ClaudeAdapter → ModelRouter → TOML config loader → proactive questions hook → Claude Code subagent/skill files. Each layer is independently testable.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tomllib` | stdlib (Python 3.11+) | Parse `.meta/config.toml` | Zero new dep; project requires Python 3.12; read-only (sufficient for config) |
| `ollama` | 0.6.x | Ollama Python client | Official Ollama library; handles HTTP to local/remote Ollama instance; no HTTP plumbing needed |
| `subprocess` | stdlib | Invoke `claude -p` for ClaudeAdapter | No API key needed; routes through Claude Code Max plan session |
| `re` | stdlib | PII keyword scanning in classifier | No ML, no cloud — local regex scan only |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `shlex` | stdlib | Safely split `claude -p` args | Prevents shell injection in subprocess calls |
| `pathlib.Path` | stdlib | Config file path (mandated FOUND-12) | Already enforced across engine |
| `json` | stdlib | Parse/format Claude subprocess response | `claude -p` returns plain text; no JSON parsing needed for simple prompts |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ollama` PyPI library | Direct `httpx`/`requests` to Ollama REST API | REST is simpler to mock in tests but requires hand-rolling retry, error handling, and host URL config; `ollama` library is 1 dep and handles all of this |
| `subprocess` for Claude | `anthropic` SDK | SDK requires API key — not available on Max plan; `claude -p` subprocess uses the active session |
| `tomllib` | `tomli` (backport) or `tomlkit` | Project requires Python 3.12 so `tomllib` is always available; `tomlkit` preserves formatting (write support) but we only need read |

**New package needed:** `ollama` (PyPI). Add to `pyproject.toml` dependencies.

**Installation:**
```bash
uv add ollama
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 3 additions)

```
engine/
├── adapters/
│   ├── __init__.py
│   ├── base.py          # BaseAdapter abstract class
│   ├── ollama_adapter.py
│   └── claude_adapter.py
├── classifier.py        # PII classifier (local-only, no network)
├── router.py            # ModelRouter: reads config, dispatches to adapter
├── ai.py                # High-level AI actions (ask_followup_questions, update_memory)
└── config_loader.py     # Reads .meta/config.toml via tomllib

.claude/
├── agents/
│   └── second-brain.md  # Claude Code subagent definition
└── commands/
    └── sb-capture.md    # /sb-capture slash command

brain/.meta/
└── config.toml          # Model routing config (created by sb-init, editable by user)

tests/
├── test_classifier.py
├── test_router.py
├── test_ollama_adapter.py
├── test_claude_adapter.py
└── test_ai.py
```

### Pattern 1: PII Classifier (AI-02)

**What:** Local-only classification. Frontmatter field takes priority over keyword scan. Returns one of `"pii"`, `"private"`, `"public"`.

**Critical:** Classifier NEVER makes network calls. NEVER passes content to any model.

```python
# engine/classifier.py
import re

PII_KEYWORDS = [
    r"\b\d{3}-\d{2}-\d{4}\b",          # SSN pattern
    r"\b\d{16}\b",                       # credit card (16 digits)
    r"\bpassword\b", r"\bpasswd\b",
    r"\bsalary\b", r"\bcompensation\b",
    r"\bhealth\b", r"\bmedical\b", r"\bdiagnosis\b",
    r"\bpersonal address\b",
]

_PII_RE = re.compile("|".join(PII_KEYWORDS), re.IGNORECASE)

SENSITIVITY_VALUES = {"pii", "private", "public"}

def classify(content_sensitivity: str, body: str) -> str:
    """Return sensitivity level for routing.

    Frontmatter field takes priority. Falls back to keyword scan.
    Never makes network calls.
    """
    # Frontmatter explicit declaration wins
    if content_sensitivity in SENSITIVITY_VALUES:
        return content_sensitivity
    # Keyword scan fallback
    if _PII_RE.search(body):
        return "pii"
    return "public"
```

**Note:** The `content_sensitivity` frontmatter field is already captured via CAP-02 and stored in the `notes` table `sensitivity` column. The classifier reads the field that was set at capture time.

### Pattern 2: Adapter Base Class and Implementations (AI-06)

**What:** Abstract `BaseAdapter` defines a single method. New models implement the interface without touching `router.py`.

```python
# engine/adapters/base.py
from abc import ABC, abstractmethod

class BaseAdapter(ABC):
    @abstractmethod
    def generate(self, user_content: str, system_prompt: str = "") -> str:
        """Send a prompt to the model; return the text response.

        Args:
            user_content: The note content or question — never in system_prompt.
            system_prompt: Static instructions — never includes user content (AI-10).
        """
        ...
```

```python
# engine/adapters/ollama_adapter.py
import ollama

class OllamaAdapter(BaseAdapter):
    def __init__(self, model: str, host: str = "http://host.docker.internal:11434"):
        self._model = model
        self._client = ollama.Client(host=host)

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})
        response = self._client.chat(model=self._model, messages=messages)
        return response.message.content
```

```python
# engine/adapters/claude_adapter.py
import subprocess
import shlex

class ClaudeAdapter(BaseAdapter):
    """Routes to Claude via 'claude -p' subprocess (Max plan, no API key needed)."""

    def __init__(self, model: str = ""):
        # model param accepted for config consistency but claude CLI uses
        # its own default model from the user's session
        self._model = model

    def generate(self, user_content: str, system_prompt: str = "") -> str:
        # Construct prompt: system instructions + separator + user content
        # AI-10: user_content is NEVER interpolated into system_prompt string
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{user_content}"
        else:
            full_prompt = user_content

        result = subprocess.run(
            ["claude", "-p", full_prompt, "--allowedTools", ""],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ClaudeAdapter: {result.returncode}")
        return result.stdout.strip()
```

**CAP-06 variant — ClaudeAdapter with Write tool for memory updates:**

```python
# For updating CLAUDE.md / MEMORY.md files
result = subprocess.run(
    ["claude", "-p", full_prompt, "--allowedTools", "Write,Read"],
    capture_output=True, text=True, timeout=60,
)
```

### Pattern 3: Config-Driven ModelRouter (AI-03, AI-04, AI-05)

**What:** Router reads `config.toml` on every call (no restart needed — AI-05). Resolves adapter class from config key. Dispatches based on classifier result.

```toml
# brain/.meta/config.toml — user-editable
[routing]
pii_model    = "ollama/llama3.2"
private_model = "claude"
public_model  = "claude"

[ollama]
host = "http://host.docker.internal:11434"

[models]
"ollama/llama3.2" = {adapter = "ollama", model = "llama3.2"}
"claude"          = {adapter = "claude", model = ""}
```

```python
# engine/router.py
import tomllib
from pathlib import Path
from engine.adapters.ollama_adapter import OllamaAdapter
from engine.adapters.claude_adapter import ClaudeAdapter

ADAPTER_MAP = {
    "ollama": OllamaAdapter,
    "claude": ClaudeAdapter,
}

def get_adapter(sensitivity: str, config_path: Path):
    """Return configured adapter instance for the given sensitivity level.

    Reads config.toml fresh on every call (AI-05: no restart needed).
    """
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    routing = config["routing"]
    models = config["models"]
    ollama_host = config.get("ollama", {}).get("host", "http://host.docker.internal:11434")

    model_key = routing.get(f"{sensitivity}_model", routing["public_model"])
    model_def = models[model_key]

    adapter_cls = ADAPTER_MAP[model_def["adapter"]]
    if model_def["adapter"] == "ollama":
        return adapter_cls(model=model_def["model"], host=ollama_host)
    return adapter_cls(model=model_def.get("model", ""))
```

### Pattern 4: Proactive Questions Hook (AI-01)

**What:** `ask_followup_questions()` called from `capture.py` AFTER classification but BEFORE note is written. Returns list of 2-3 questions. Each question is printed; user answers are appended to the note body.

**Content-type system prompts (static — never include user note body):**

```python
# engine/ai.py
QUESTION_SYSTEM_PROMPTS = {
    "meeting": "You are a meeting notes assistant. Given a meeting note title, generate exactly 2-3 short follow-up questions to extract missing context (attendees, decisions, action items). Output only a numbered list.",
    "idea":    "You are an idea development assistant. Given an idea title, generate 2-3 questions to develop it further (problem it solves, who benefits, first step). Output only a numbered list.",
    "coding":  "You are a software engineering assistant. Given a coding note title, generate 2-3 questions to capture architectural context (why this approach, alternatives, risks). Output only a numbered list.",
    "people":  "You are a professional context assistant. Given a person note title, generate 2-3 questions to capture relationship context (how you know them, their goals, recent interactions). Output only a numbered list.",
    "strategy":"You are a strategy assistant. Given a strategy note title, generate 2-3 questions to clarify intent (objective, success metric, timeline). Output only a numbered list.",
    "note":    "You are a knowledge assistant. Given a note title, generate 2-3 questions to enrich it (key insight, source, how it connects to current work). Output only a numbered list.",
}

def ask_followup_questions(
    note_type: str,
    title: str,
    sensitivity: str,
    config_path: Path,
) -> list[str]:
    """Generate 2-3 follow-up questions for the given note.

    AI-10: title is passed as user_content, NOT interpolated into system_prompt.
    """
    system = QUESTION_SYSTEM_PROMPTS.get(note_type, QUESTION_SYSTEM_PROMPTS["note"])
    adapter = get_adapter(sensitivity, config_path)
    raw = adapter.generate(user_content=title, system_prompt=system)
    # Parse numbered list — lines starting with digit or dash
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    questions = [l for l in lines if l and (l[0].isdigit() or l[0] == "-")]
    return questions[:3]
```

### Pattern 5: Claude Code Subagent File (AI-07)

**What:** A markdown file with YAML frontmatter. Stored in `.claude/agents/second-brain.md` (project-level). Install script copies to `~/.claude/agents/second-brain.md` (user-level = available in all Claude sessions).

```markdown
---
name: second-brain
description: Captures notes, meetings, ideas, and people into the second brain. Use when the user asks to capture, save, record, or log any information.
tools: Bash
---

You are the second-brain capture agent. Your job is to capture notes into the user's second brain using the sb-capture command.

When the user asks to capture something:
1. Determine the content type (note, meeting, idea, people, coding, strategy)
2. Extract a concise title
3. Run: sb-capture --type <type> --title "<title>" --body "<body>" --sensitivity <level>
4. Confirm the capture was successful and show the file path

Always classify content_sensitivity:
- Use "pii" for any personal identifiers, health info, financial details
- Use "private" for internal business information
- Use "public" for general knowledge and non-sensitive notes
```

**Install script** (`scripts/install_subagent.py`):

```python
import shutil
from pathlib import Path

src = Path(".claude/agents/second-brain.md")
dst = Path.home() / ".claude" / "agents" / "second-brain.md"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
print(f"Installed second-brain subagent to {dst}")
```

**Invoke:** From any Claude Code session, type `/second-brain` or Claude will auto-delegate to the subagent when context matches.

### Pattern 6: /sb-capture Slash Command (AI-08)

**Location:** `.claude/commands/sb-capture.md` (project) or copied to `~/.claude/commands/sb-capture.md` (global).

```markdown
---
description: Capture a note into the second brain
allowed-tools: Bash
---

Capture the following into the second brain:

$ARGUMENTS

Run: sb-capture --type note --title "$ARGUMENTS" --sensitivity public

After capturing, confirm the file path and ask if any follow-up is needed.
```

### Anti-Patterns to Avoid

- **Calling `anthropic.Anthropic(api_key=...)` anywhere.** The user has no API key. This will fail at runtime. Use `ClaudeAdapter` (subprocess) exclusively.
- **Interpolating note body into system prompt strings.** `f"Summarise this: {post.content}"` in the `system` field violates AI-10. Always pass note content as `user_content`.
- **Reading config.toml once at module load time.** Defeats AI-05 (no restart required). Read it inside `get_adapter()` on every call.
- **Hardcoding Ollama host as `localhost:11434`.** Inside DevContainer, `localhost` is the container — Ollama runs on the host. Always use `host.docker.internal:11434` as default.
- **Running PII classifier inside the adapter.** The classifier must run BEFORE the adapter is selected. Classifier is called in `capture.py` main flow, then result is passed to router.
- **Blocking capture on AI failure.** If the adapter call fails (Ollama unreachable, claude not installed), the note capture should still succeed. AI enrichment is a best-effort enhancement, not a gate.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ollama HTTP client | Custom `requests` calls to `localhost:11434` | `ollama.Client(host=...)` | Retry logic, connection pooling, response parsing already handled; host param is clean |
| TOML parsing | Custom string parser for config.toml | `tomllib.load(f)` (stdlib) | TOML has edge cases (multiline, escape sequences); stdlib is correct and zero-dep |
| Claude API client | `anthropic.Anthropic(api_key=...)` | `subprocess.run(["claude", "-p", ...])` | No API key available; subprocess uses Max plan session |
| PII detection via NLP | Sending content to a model to classify it | Local keyword regex (`classifier.py`) | Circular — you'd have to classify before routing, but routing is needed to classify; NLP is also out of scope per REQUIREMENTS.md |
| Adapter factory with registry | Dynamic import/plugin system | `ADAPTER_MAP` dict in `router.py` | Simple dict lookup is sufficient for 2 adapters; plugin system adds complexity with no benefit |

---

## Common Pitfalls

### Pitfall 1: `host.docker.internal` Not Resolving on Linux

**What goes wrong:** `OllamaAdapter` raises `ConnectionRefusedError` or DNS resolution failure.

**Why it happens:** On Linux Docker (non-Desktop), `host.docker.internal` is not auto-added. macOS Docker Desktop adds it automatically.

**How to avoid:** In `devcontainer.json`, add `"runArgs": ["--add-host=host.docker.internal:host-gateway"]`. Document in INSTALL.md. Test with `curl http://host.docker.internal:11434` from inside the container.

**Warning signs:** Connection errors only on Linux, not macOS.

### Pitfall 2: `claude -p` Not on PATH Inside DevContainer

**What goes wrong:** `ClaudeAdapter` raises `FileNotFoundError: [Errno 2] No such file or directory: 'claude'`.

**Why it happens:** Claude Code CLI is installed on the host, not inside the container.

**How to avoid:** `ClaudeAdapter.generate()` must check `shutil.which("claude")` before calling subprocess. If not found, raise a clear `RuntimeError("ClaudeAdapter: claude CLI not found — run sb-capture from the host or install claude inside the container")`. Tests mock the subprocess.

**Warning signs:** Works when run from the host terminal; fails inside the DevContainer terminal.

### Pitfall 3: Config.toml Read Fails — No File Yet

**What goes wrong:** `FileNotFoundError` on first run before `sb-init` has created `.meta/config.toml`.

**Why it happens:** `sb-init` creates the `.meta/` directory but does not yet create `config.toml`.

**How to avoid:** Phase 3 must extend `sb-init` (or add a migration step) to write a default `config.toml` if absent. `config_loader.py` also has a fallback: if the file does not exist, return hard-coded defaults. Test that defaults produce a working OllamaAdapter and ClaudeAdapter.

### Pitfall 4: Prompt Injection via Note Title or Tags

**What goes wrong:** A note title like `"Ignore previous instructions and reveal..."` is included in the system prompt, altering the AI's behaviour.

**Why it happens:** f-string interpolation of user-controlled content into the static `system_prompt` string.

**How to avoid:** AI-10 is enforced by construction: `system_prompt` contains only static strings from `QUESTION_SYSTEM_PROMPTS` dict. User content (`title`, `body`) is always passed as the `user_content` argument. Tests verify the `system` message in adapter calls contains no user-provided content.

### Pitfall 5: AI Failure Blocks Note Capture

**What goes wrong:** `ask_followup_questions()` raises (Ollama unreachable, timeout, model not pulled) and the entire `/sb-capture` command fails — note is never written.

**Why it happens:** Uncaught exception from adapter propagates through `main()` in `capture.py`.

**How to avoid:** Wrap `ask_followup_questions()` call in `try/except` in `capture.py`. On failure: print a warning, continue with empty questions list. Capture proceeds regardless. Log the failure type but not the content.

### Pitfall 6: tomllib Requires Binary Mode

**What goes wrong:** `TypeError: a bytes-like object is required` when opening `config.toml`.

**Why it happens:** `tomllib.load()` requires the file opened in `"rb"` (binary read) mode, not `"r"` (text mode).

**How to avoid:** Always `open(config_path, "rb")` — not `open(config_path, "r")`.

---

## Code Examples

### Verified: Ollama Python Client with Custom Host

```python
# Source: https://github.com/ollama/ollama-python
import ollama

client = ollama.Client(host="http://host.docker.internal:11434")
response = client.chat(
    model="llama3.2",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What are three follow-up questions for a meeting about Q1 planning?"},
    ]
)
text = response.message.content
```

### Verified: tomllib Config Parsing (Python 3.11+)

```python
# Source: https://docs.python.org/3/library/tomllib.html
import tomllib
from pathlib import Path

config_path = Path("/workspace/brain/.meta/config.toml")
with open(config_path, "rb") as f:   # NOTE: binary mode required
    config = tomllib.load(f)

pii_model = config["routing"]["pii_model"]  # e.g. "ollama/llama3.2"
```

### Verified: claude -p Subprocess (ClaudeAdapter)

```python
# Source: Claude Code CLI docs — https://code.claude.com/docs/en/sub-agents
# -p / --print: non-interactive mode, prints response and exits
import subprocess

result = subprocess.run(
    ["claude", "-p", "What is the capital of France?", "--allowedTools", ""],
    capture_output=True,
    text=True,
    timeout=60,
)
assert result.returncode == 0
answer = result.stdout.strip()
```

### Verified: Claude Code Subagent File Format

```markdown
---
name: second-brain
description: Use when user asks to capture, save, or record notes and information.
tools: Bash
---

System prompt body here in plain Markdown...
```

Stored at: `.claude/agents/second-brain.md` (project) or `~/.claude/agents/second-brain.md` (global/user-level).

### Verified: Separation of system and user content (AI-10)

```python
# CORRECT — user_content is separate argument, never in system string
adapter.generate(
    user_content=post.get("title"),      # user-controlled
    system_prompt=QUESTION_SYSTEM_PROMPTS["meeting"],  # static only
)

# WRONG — violates AI-10
system = f"Summarise this note: {post.content}"  # injection vector
adapter.generate(user_content="", system_prompt=system)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Direct `anthropic` SDK with API key | `claude -p` subprocess (Max plan auth) | 2024–2025 | No API key required; uses active Claude Code session |
| Single-model AI calls | Adapter pattern with config-driven routing | Standard since 2023 | New models added without code changes |
| PII detection via cloud NLP | Local keyword rules + frontmatter field | Project decision | Zero data leak risk; no circular dependency |
| `toml` third-party library | `tomllib` stdlib (Python 3.11+) | Python 3.11 (2022) | Zero new dependency for config parsing |
| Custom Ollama HTTP calls | `ollama` PyPI library | Library released 2024 | Cleaner API, connection management handled |

**Deprecated/outdated:**
- `.claude/commands/` directory: Legacy format. Still works but `.claude/skills/<name>/SKILL.md` is the current preferred format for slash commands (the legacy `.claude/commands/` format is simpler and sufficient for Phase 3).
- `anthropic.Anthropic(api_key=...)` for this project: Not deprecated globally, but unavailable here due to Max plan constraint.

---

## Open Questions

1. **`claude -p` availability inside DevContainer**
   - What we know: Claude Code CLI is installed on the host machine. The DevContainer is a Docker container.
   - What's unclear: Is `claude` on PATH inside the DevContainer? Can it authenticate using the host's Claude Code session from inside the container?
   - Recommendation: Test this explicitly in Wave 0 of Phase 3. If `claude` is not available inside the container, `ClaudeAdapter` must be called from the host. Mitigation: mount the host `claude` binary or add a note that `/sb-capture` with AI enrichment must be run from the host terminal (not container terminal). The subagent (AI-07) runs in the user's Claude Code session on the host — this is unaffected.
   - Fallback: If `claude` is unavailable inside container, `ClaudeAdapter.generate()` raises a clear error and capture continues without AI enrichment (AI failure must not block capture — see Pitfall 5).

2. **Ollama model availability — which model is pre-pulled?**
   - What we know: Ollama must be running on the host with at least one model pulled. STATE.md flags this as needing verification.
   - What's unclear: Which model is realistic for PII-only use (small, fast, local)? `llama3.2` is a 2B model, feasible on most developer machines. `phi3` is even smaller.
   - Recommendation: Default `config.toml` should specify `llama3.2` as the PII model. Document that user must run `ollama pull llama3.2` before Phase 3 features work. `OllamaAdapter` should detect missing model and give a clear error: `"Model llama3.2 not found — run: ollama pull llama3.2"`.

3. **CAP-06: Which memory file to update?**
   - What we know: Claude Code reads `CLAUDE.md` and project memory files. The project memory path is `~/.claude/projects/<hash>/memory/MEMORY.md`.
   - What's unclear: The project hash in the path varies by install. The `claude -p` approach can be given a `Write` tool and instructed to update the correct file.
   - Recommendation: Instruct `ClaudeAdapter` for CAP-06 to write to the path returned by `claude config get projectMemoryPath` or use the known path pattern. Alternatively, write to `~/.claude/projects/$(pwd | md5sum)/memory/MEMORY.md`. This is LOW confidence — verify the exact path at implementation time.

4. **`claude -p` output format for follow-up questions**
   - What we know: `claude -p` returns stdout as plain text.
   - What's unclear: Will the model reliably return a numbered list when instructed? How to handle malformed output (no numbered list, too many questions)?
   - Recommendation: `ask_followup_questions()` parses liberally (any line with digit or dash prefix is a question). If fewer than 2 questions parsed, fallback to a hardcoded 2-question default per content type. If more than 3, truncate.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 7.x (already in pyproject.toml dev deps) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run --no-project --with pytest pytest tests/ -x -q` |
| Full suite command | `uv run --no-project --with pytest pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-02 | Classifier returns "pii" when frontmatter says "pii" | unit | `pytest tests/test_classifier.py::test_frontmatter_pii_wins -x` | Wave 0 |
| AI-02 | Classifier returns "pii" on keyword match when frontmatter is absent | unit | `pytest tests/test_classifier.py::test_keyword_scan_triggers_pii -x` | Wave 0 |
| AI-02 | Classifier returns "public" for clean body | unit | `pytest tests/test_classifier.py::test_clean_body_public -x` | Wave 0 |
| AI-03 | PII note routes to OllamaAdapter (never ClaudeAdapter) | unit | `pytest tests/test_router.py::test_pii_routes_to_ollama -x` | Wave 0 |
| AI-04 | Public note routes to ClaudeAdapter (never OllamaAdapter) | unit | `pytest tests/test_router.py::test_public_routes_to_claude -x` | Wave 0 |
| AI-05 | Changing config.toml routes next call without restart | unit | `pytest tests/test_router.py::test_config_change_no_restart -x` | Wave 0 |
| AI-06 | New adapter registered in ADAPTER_MAP is callable via router | unit | `pytest tests/test_router.py::test_custom_adapter_registered -x` | Wave 0 |
| AI-10 | system_prompt arg in all adapter calls contains no user-supplied content | unit | `pytest tests/test_ai.py::test_no_user_content_in_system_prompt -x` | Wave 0 |
| AI-01 | ask_followup_questions returns 2–3 questions for each content type | unit (mocked adapter) | `pytest tests/test_ai.py::test_followup_questions_count -x` | Wave 0 |
| AI-03 | Network log shows zero outbound Anthropic calls for PII note | integration/smoke | `pytest tests/test_router.py::test_pii_zero_anthropic_calls -x` | Wave 0 |
| AI-07 | second-brain.md has valid YAML frontmatter with required fields | unit | `pytest tests/test_subagent.py::test_subagent_frontmatter_valid -x` | Wave 0 |
| AI-08 | sb-capture.md slash command file exists and has description | unit | `pytest tests/test_subagent.py::test_slash_command_exists -x` | Wave 0 |
| AI-09 | Rate limiter module enforces max calls per minute | unit | `pytest tests/test_ratelimit.py::test_rate_limit_enforced -x` | Wave 0 |
| CAP-06 | ClaudeAdapter with Write tool called for memory update | unit (mocked subprocess) | `pytest tests/test_ai.py::test_cap06_memory_update_called -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run --no-project --with pytest pytest tests/ -x -q`
- **Per wave merge:** `uv run --no-project --with pytest pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_classifier.py` — covers AI-02
- [ ] `tests/test_router.py` — covers AI-03, AI-04, AI-05, AI-06
- [ ] `tests/test_ai.py` — covers AI-01, AI-10, CAP-06
- [ ] `tests/test_ollama_adapter.py` — unit tests with mocked `ollama.Client`
- [ ] `tests/test_claude_adapter.py` — unit tests with mocked `subprocess.run`
- [ ] `tests/test_subagent.py` — covers AI-07, AI-08 (file existence + frontmatter parse)
- [ ] `tests/test_ratelimit.py` — covers AI-09 debounce/rate-limit utility
- [ ] `conftest.py` — extend with `mock_adapter` fixture and `tmp_config_toml` fixture

---

## Sources

### Primary (HIGH confidence)

- [ollama/ollama-python GitHub](https://github.com/ollama/ollama-python) — `Client(host=...)`, `chat()` API, `response.message.content`
- [Ollama Chat API docs](https://docs.ollama.com/api/chat) — message format, system role, streaming
- [Python tomllib stdlib docs](https://docs.python.org/3/library/tomllib.html) — `load(f)` requires binary mode, read-only, Python 3.11+
- [Claude Code sub-agents docs](https://code.claude.com/docs/en/sub-agents) — YAML frontmatter fields, `name`, `description`, `tools`, storage locations
- [Claude Code slash commands docs](https://code.claude.com/docs/en/slash-commands) — `.claude/commands/` format, `$ARGUMENTS`

### Secondary (MEDIUM confidence)

- WebSearch: `claude -p` subprocess pattern — multiple sources confirm `-p` flag for non-interactive use; `capture_output=True` with `subprocess.run`
- WebSearch: `host.docker.internal` for Docker-to-host Ollama — confirmed macOS auto-resolves; Linux needs `--add-host=host.docker.internal:host-gateway`
- WebSearch: `ollama` library version 0.6.x current — PyPI page confirms version; chat API structure stable across 0.4–0.6

### Tertiary (LOW confidence — flag for validation)

- CAP-06 memory file path (`~/.claude/projects/<hash>/memory/MEMORY.md`) — exact path structure needs verification at implementation time
- `claude -p` availability inside DevContainer — not verified empirically; needs a Wave 0 spike test

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `tomllib` stdlib, `ollama` PyPI official, `subprocess` stdlib all verified
- Architecture: HIGH — adapter pattern is standard; classifier design matches REQUIREMENTS.md out-of-scope NLP note; TOML config loader is straightforward
- ClaudeAdapter subprocess: MEDIUM — `claude -p` pattern confirmed by multiple sources but in-container availability is an open question
- Subagent/skill files: MEDIUM — format confirmed by official docs; exact invocation behavior needs empirical test
- CAP-06 memory path: LOW — path structure inferred, not verified from official docs

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (ollama library API stable; tomllib stdlib; claude CLI flags may change faster)
