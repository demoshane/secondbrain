#!/usr/bin/env python3
"""Install the second-brain Claude Code subagent to the user-level agents directory.

Run from repo root: python scripts/install_subagent.py

After installation, the 'second-brain' subagent is available in all Claude Code sessions.
"""
import shutil
from pathlib import Path

src = Path(".claude/agents/second-brain.md")
if not src.exists():
    raise FileNotFoundError(f"Subagent source not found: {src.resolve()}")

dst = Path.home() / ".claude" / "agents" / "second-brain.md"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(src, dst)
print(f"Installed: {dst}")
print("The 'second-brain' subagent is now available in all Claude Code sessions.")
print("Invoke with: ask Claude to capture something, or use /second-brain")
