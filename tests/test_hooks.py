import pytest
import engine.hooks.post_commit  # noqa: F401 — import guard


@pytest.mark.xfail(strict=False, reason="stub — CAP-05 implementation pending")
def test_get_commit_info():
    """get_commit_info() returns message, stat, repo name from mocked git subprocess."""
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="stub — CAP-05 implementation pending")
def test_initial_commit_fallback():
    """get_commit_info() falls back to git show when HEAD~1 does not exist."""
    raise NotImplementedError


@pytest.mark.xfail(strict=False, reason="stub — CAP-05 implementation pending")
def test_non_interactive_skips_prompt():
    """main() skips input() when sys.stdin is not a TTY."""
    raise NotImplementedError
