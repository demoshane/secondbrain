# Security — Second Brain Project

Last updated: 2026-03-19

Project-specific security details. For global Claude Code security practices, see `~/.claude/SECURITY.md`.

---

## MCP Tools Data Exposure

Second Brain MCP tools (`sb_*`) return note content to Claude Code, which enters the conversation context and is sent to Anthropic's API.

| Tool | Data returned |
|------|-------------|
| `sb_search` | Note snippets matching query |
| `sb_read` | Full note body |
| `sb_person_context` | Person note + meetings + actions + mentions |
| `sb_recap` | Recent notes + action items summary |
| `sb_actions` | Action item text, assignees |
| `sb_connections` | Related note titles and paths |
| `sb_files` | File metadata (name, path) — not file contents |

**PII gate**: Notes with `sensitivity: pii` are summarized via local Ollama before reaching Claude Code.

---

## Devcontainer Isolation

### Shared with host (bind-mounted)

| Mount | Host path | Container path | Access |
|-------|-----------|----------------|--------|
| Repository | `~/second-brain/` | `/workspace/` | Read + Write |
| Brain notes | `~/SecondBrain/` | `/workspace/brain/` | Read + Write |
| Claude config | `~/.claude/` | `/home/vscode/.claude/` | Read + Write |
| Git identity | `~/.gitconfig` | `/home/vscode/.gitconfig` | Read only |

### Isolated from host

- **SSH keys** — NOT mounted, git push blocked
- **SQLite index** — Docker named volume, separate from host DB
- **Python/Node envs** — Container-local, host `.venv` untouched

### Guardrails (active even with `--dangerously-skip-permissions`)

1. **`guardrail-hook.sh`** — blocks bulk brain deletion, credential file reads, config mutation
2. **`claude-dev.sh`** — system prompt safety rules for destructive operation confirmation

---

## Two-Step Token Pattern

Destructive MCP operations (`sb_forget`, `sb_anonymize`) require two calls:
1. First call returns a `confirm_token` (expires in 60s)
2. Second call with token executes the operation

This prevents accidental deletion from a single misunderstood instruction.
