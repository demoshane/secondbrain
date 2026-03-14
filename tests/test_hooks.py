import sys
from unittest.mock import MagicMock, patch

import engine.hooks.post_commit  # noqa: F401 — import guard


def _make_run_side_effect(message="fix: typo", stat="1 file changed", repo="/tmp/my-project"):
    """Return a side_effect function for subprocess.run covering all three git calls."""

    def side_effect(args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        if "log" in args:
            mock.stdout = message + "\n"
        elif "diff" in args:
            mock.stdout = stat + "\n"
        elif "show" in args:
            mock.stdout = stat + "\n"
        elif "rev-parse" in args:
            mock.stdout = repo + "\n"
        else:
            mock.stdout = ""
        return mock

    return side_effect


def test_get_commit_info():
    """get_commit_info() returns message, stat, repo name from mocked git subprocess."""
    side_effect = _make_run_side_effect(
        message="fix: typo", stat="1 file changed", repo="/tmp/my-project"
    )
    with patch("engine.hooks.post_commit.subprocess.run", side_effect=side_effect):
        from engine.hooks.post_commit import get_commit_info

        result = get_commit_info()

    assert result["message"] == "fix: typo"
    assert result["stat"] == "1 file changed"
    assert result["repo"] == "my-project"


def test_initial_commit_fallback():
    """get_commit_info() falls back to git show when HEAD~1 does not exist (returncode=128)."""

    def side_effect(args, **kwargs):
        mock = MagicMock()
        if "log" in args:
            mock.returncode = 0
            mock.stdout = "initial: setup\n"
        elif "diff" in args:
            # Simulate initial commit — HEAD~1 does not exist
            mock.returncode = 128
            mock.stdout = ""
        elif "show" in args:
            mock.returncode = 0
            mock.stdout = "2 files changed, 10 insertions(+)\n"
        elif "rev-parse" in args:
            mock.returncode = 0
            mock.stdout = "/tmp/my-project\n"
        else:
            mock.returncode = 0
            mock.stdout = ""
        return mock

    with patch("engine.hooks.post_commit.subprocess.run", side_effect=side_effect):
        from engine.hooks.post_commit import get_commit_info

        result = get_commit_info()

    assert result["stat"] != ""
    assert "files changed" in result["stat"] or "insertions" in result["stat"]


def test_non_interactive_skips_prompt(capsys):
    """main() skips input() when sys.stdin is not a TTY."""
    mock_adapter = MagicMock()
    mock_adapter.generate.return_value = "summary text"

    with (
        patch("engine.hooks.post_commit.get_commit_info", return_value={
            "message": "fix: typo",
            "stat": "1 file changed",
            "repo": "my-project",
        }),
        patch("engine.router.get_adapter", return_value=mock_adapter),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = False

        from engine.hooks.post_commit import main

        main()

    captured = capsys.readouterr()
    assert "non-interactive" in captured.err
    # input() should never have been called
    mock_stdin.readline.assert_not_called()
