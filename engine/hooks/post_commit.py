"""Git post-commit hook helper (CAP-05).

Installed per-project by user:
    git config core.hooksPath /path/to/brain/.githooks

The shell hook cds to the brain repo so `uv run` finds the right venv,
then passes the original project directory via SB_PROJECT_DIR so git
commands here still target the correct repo.
"""
import os
import subprocess
import sys
from pathlib import Path


def get_commit_info() -> dict:
    """Extract commit subject, file stat diff, and repo name from HEAD.

    Returns dict with keys: message (str), stat (str), repo (str).
    Falls back to `git show --stat HEAD` if HEAD~1 does not exist (initial commit).
    """
    project_dir = os.environ.get("SB_PROJECT_DIR")
    git = ["git", "-C", project_dir] if project_dir else ["git"]

    message = subprocess.run(
        git + ["log", "-1", "--format=%s", "HEAD"],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip()

    stat_result = subprocess.run(
        git + ["diff", "HEAD~1", "HEAD", "--stat"],
        capture_output=True, text=True, timeout=10,
    )
    if stat_result.returncode != 0:
        # Initial commit: no HEAD~1
        stat_result = subprocess.run(
            git + ["show", "--stat", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    stat = stat_result.stdout.strip()

    repo_result = subprocess.run(
        git + ["rev-parse", "--show-toplevel"],
        capture_output=True, text=True, timeout=10,
    )
    repo = Path(repo_result.stdout.strip()).name if repo_result.returncode == 0 else "unknown"

    return {"message": message, "stat": stat, "repo": repo}


def main() -> None:
    """Entry point: summarize latest git commit and offer to link it to the brain."""
    from engine.router import get_adapter
    from engine.paths import CONFIG_PATH

    info = get_commit_info()
    adapter = get_adapter("public", CONFIG_PATH)
    system = (
        "You are a commit summarizer. Given a git commit message and file stat diff, "
        "write a single plain-English sentence summarizing what changed and why. "
        "Output only the summary sentence — no preamble."
    )
    user_content = f"Commit: {info['message']}\n\nFiles changed:\n{info['stat']}"
    try:
        summary = adapter.generate(user_content=user_content, system_prompt=system)
    except Exception as e:
        print(f"[sb-hook] AI summary unavailable: {type(e).__name__}", file=sys.stderr)
        return

    print(f"\n[second-brain] {info['repo']}: {summary}")

    if not sys.stdin.isatty():
        print("[sb-hook] non-interactive: skipping brain link prompt", file=sys.stderr)
        return

    answer = input("Link this commit to a brain entry? [y/N]: ").strip().lower()
    if answer != "y":
        return

    title = input("Brain entry title (or press Enter to skip): ").strip()
    if not title:
        return

    from engine.capture import capture_note
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT

    conn = get_connection()
    init_schema(conn)
    capture_note(
        "coding", title, summary, [], [], "public", BRAIN_ROOT, conn,
    )
    conn.close()
    print("[second-brain] Brain entry created.")


if __name__ == "__main__":
    main()
