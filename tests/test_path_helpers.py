"""Tests for store_path() and resolve_path() helpers in engine/paths.py.

TDD RED phase — these tests must fail until the helpers are implemented.
"""
import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def brain_root_patch(tmp_path, monkeypatch):
    """Patch engine.paths.BRAIN_ROOT to a tmp_path subdirectory."""
    import engine.paths as _paths
    root = tmp_path / "SecondBrain"
    root.mkdir()
    monkeypatch.setattr(_paths, "BRAIN_ROOT", root)
    return root


class TestStorePath:
    def test_absolute_inside_brain_returns_relative(self, brain_root_patch):
        from engine.paths import store_path
        brain = brain_root_patch
        abs_path = brain / "coding" / "note.md"
        result = store_path(abs_path)
        assert result == "coding/note.md"

    def test_absolute_string_inside_brain_returns_relative(self, brain_root_patch):
        from engine.paths import store_path
        brain = brain_root_patch
        abs_path = str(brain / "meetings" / "2026-01-01-kickoff.md")
        result = store_path(abs_path)
        assert result == "meetings/2026-01-01-kickoff.md"

    def test_already_relative_returns_unchanged(self, brain_root_patch):
        from engine.paths import store_path
        result = store_path("coding/note.md")
        assert result == "coding/note.md"

    def test_already_relative_no_slash_prefix(self, brain_root_patch):
        from engine.paths import store_path
        result = store_path("ideas/my-idea.md")
        assert result == "ideas/my-idea.md"

    def test_outside_brain_root_raises_value_error(self, brain_root_patch):
        from engine.paths import store_path
        outside_path = "/tmp/not-in-brain/note.md"
        with pytest.raises(ValueError, match="outside BRAIN_ROOT"):
            store_path(outside_path)

    def test_path_object_accepted(self, brain_root_patch):
        from engine.paths import store_path
        brain = brain_root_patch
        result = store_path(Path(str(brain / "strategy" / "plan.md")))
        assert result == "strategy/plan.md"

    def test_deeply_nested_path(self, brain_root_patch):
        from engine.paths import store_path
        brain = brain_root_patch
        abs_path = brain / "projects" / "subdir" / "note.md"
        result = store_path(abs_path)
        assert result == "projects/subdir/note.md"


class TestResolvePath:
    def test_relative_path_resolves_to_absolute(self, brain_root_patch):
        from engine.paths import resolve_path
        brain = brain_root_patch
        result = resolve_path("coding/note.md")
        assert result == brain / "coding" / "note.md"
        assert isinstance(result, Path)

    def test_absolute_path_returned_unchanged(self, brain_root_patch):
        """Backward compat: resolve_path on an already-absolute path returns it as Path."""
        from engine.paths import resolve_path
        abs_path = "/Users/x/SecondBrain/coding/note.md"
        result = resolve_path(abs_path)
        assert result == Path(abs_path)
        assert isinstance(result, Path)

    def test_path_object_relative_resolves(self, brain_root_patch):
        from engine.paths import resolve_path
        brain = brain_root_patch
        result = resolve_path(Path("meetings/2026-01-01-kickoff.md"))
        assert result == brain / "meetings" / "2026-01-01-kickoff.md"

    def test_deeply_nested_relative(self, brain_root_patch):
        from engine.paths import resolve_path
        brain = brain_root_patch
        result = resolve_path("projects/alpha/notes.md")
        assert result == brain / "projects" / "alpha" / "notes.md"


class TestRoundTrip:
    def test_store_then_resolve_round_trips(self, brain_root_patch):
        """store_path → resolve_path gives back the original absolute path."""
        from engine.paths import store_path, resolve_path
        brain = brain_root_patch
        original = brain / "coding" / "my-note.md"
        stored = store_path(original)
        resolved = resolve_path(stored)
        assert resolved == original

    def test_resolve_then_store_round_trips(self, brain_root_patch):
        """resolve_path → store_path gives back the relative string."""
        from engine.paths import store_path, resolve_path
        rel = "strategy/q2-plan.md"
        resolved = resolve_path(rel)
        stored = store_path(resolved)
        assert stored == rel
