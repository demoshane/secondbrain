# Second Brain

Personal knowledge management system built on a DevContainer + SQLite + Google Drive.

---

## Prerequisites

These must be in place **on the host (macOS)** before opening the DevContainer.

### 1. Docker Desktop
Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).

### 2. VS Code + Dev Containers extension
Install the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension.

### 3. Google Drive folder
`~/SecondBrain` must exist and be syncing with Google Drive before opening the container.

```bash
mkdir -p ~/SecondBrain
```

### 4. Environment file
Create `.env.host` outside the Drive-synced folder (so secrets are never synced):

```bash
mkdir -p ~/.config/second-brain
cp .env.host.example ~/.config/second-brain/.env.host
# Edit the file and fill in your secrets:
#   ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 5. Activate git hooks (one-time, after cloning)
The repo ships a portable hook in `.githooks/`. Point git at it with:

```bash
git config core.hooksPath .githooks
```

> DevContainer does this automatically in `postCreateCommand`. Host users must run this once after cloning.
>
> Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) on the host (`brew install uv` on macOS).

### 6. Git identity
Ensure `~/.gitconfig` has your name and email (it is bind-mounted into the container):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

---

## Opening the DevContainer

1. Open this repo in VS Code
2. `Ctrl+Shift+P` → **Dev Containers: Reopen in Container**
3. Wait for the build and `postCreateCommand` to complete (~2–5 min on first build)

Everything else is automatic:
- Python deps installed (`uv pip install -e '.[dev]'`)
- git hooks path set to `.githooks/` (`git config core.hooksPath .githooks`)
- Claude Code installed globally
- SQLite volume ownership fixed

---

## Verify the setup

Run inside the container:

```bash
uv run python scripts/bootstrap.py --dev
# Expected: all checks [PASS]

uv run sb-init
# Expected: [PASS] Drive mount; [CREATED/EXISTS] 9 subdirs; [OK] Schema; [OK] .vscode/settings.json

uv run sb-reindex
# Expected: [OK] Indexed 0 notes (on a fresh brain)
```

---

## Windows / WSL2

`${localEnv:HOME}` in `devcontainer.json` may resolve to the Windows path instead of the WSL2 path, causing the brain bind mount to fail. If this happens, replace `${localEnv:HOME}` in `.devcontainer/devcontainer.json` with the explicit WSL2 path (e.g., `/home/yourname`).

---

## Known limitations

- **Anthropic API keys are not caught by `detect-secrets`** — no built-in plugin exists for the `sk-ant-api03-*` format. The pre-commit hook protects via baseline diff and other pattern detectors (private keys, high-entropy strings, etc.).
