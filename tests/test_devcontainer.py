import json
import re
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).parent.parent
DEVCONTAINER_JSON = REPO_ROOT / ".devcontainer" / "devcontainer.json"
DOCKERFILE = REPO_ROOT / ".devcontainer" / "Dockerfile"


def _parse_devcontainer():
    """Parse devcontainer.json, stripping JSONC // comments."""
    raw = DEVCONTAINER_JSON.read_text()
    stripped = re.sub(r"^\s*//.*$", "", raw, flags=re.MULTILINE)
    return json.loads(stripped)


# --- Dockerfile tests (Task 1) ---

def test_dockerfile_vscode_user_arg():
    content = DOCKERFILE.read_text()
    assert "ARG USERNAME=vscode" in content, "Dockerfile must declare ARG USERNAME=vscode"


def test_dockerfile_final_user_is_vscode():
    content = DOCKERFILE.read_text()
    # USER $USERNAME must appear and must not be followed by USER root
    assert "USER $USERNAME" in content, "Dockerfile must switch to USER $USERNAME"
    # Ensure no 'USER root' after the vscode user block
    lines = content.splitlines()
    last_user = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("USER "):
            last_user = stripped
    assert last_user == "USER $USERNAME", f"Final USER directive must be 'USER $USERNAME', got: {last_user}"


def test_dockerfile_workdir_workspace():
    content = DOCKERFILE.read_text()
    assert "WORKDIR /workspace" in content


# --- devcontainer.json tests (Task 2) ---

def test_remote_user():
    parsed = _parse_devcontainer()
    assert parsed["remoteUser"] == "vscode", f"remoteUser must be 'vscode', got: {parsed.get('remoteUser')}"


def test_brain_mount_present():
    parsed = _parse_devcontainer()
    mounts = parsed.get("mounts", [])
    assert any(
        "SecondBrain" in m and "/workspace/brain" in m for m in mounts
    ), "mounts must contain an entry with SecondBrain source and /workspace/brain target"


def test_env_host_mount_outside_drive():
    parsed = _parse_devcontainer()
    mounts = parsed.get("mounts", [])
    env_mounts = [m for m in mounts if ".env.host" in m]
    assert env_mounts, "mounts must contain an .env.host entry"
    for m in env_mounts:
        assert ".config/second-brain" in m, (
            f".env.host mount source must use .config/second-brain path, not SecondBrain/: {m}"
        )
        assert "SecondBrain/" not in m, (
            f".env.host must NOT be sourced from inside SecondBrain/ (Drive-synced): {m}"
        )
