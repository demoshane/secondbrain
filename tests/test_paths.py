import ast
import sys
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ENGINE_DIR = REPO_ROOT / "engine"


def _python_files_in_engine():
    return list(ENGINE_DIR.rglob("*.py"))


def test_engine_files_exist():
    """Sanity check — engine/ must have at least paths.py, db.py, init_brain.py, reindex.py."""
    expected = ["paths.py", "db.py", "init_brain.py", "reindex.py"]
    for name in expected:
        assert (ENGINE_DIR / name).exists(), f"engine/{name} missing"


def test_no_os_path_join_in_engine():
    """engine/ must not use os.path.join — use pathlib.Path / operator instead (FOUND-12)."""
    violations = []
    for py_file in _python_files_in_engine():
        content = py_file.read_text()
        if "os.path.join" in content:
            violations.append(str(py_file.relative_to(REPO_ROOT)))
    assert not violations, f"os.path.join found in: {violations}"


def test_no_hardcoded_separators():
    """engine/ files (except paths.py) must not hardcode /workspace/brain."""
    violations = []
    for py_file in _python_files_in_engine():
        if py_file.name == "paths.py":
            continue  # paths.py is the single source of truth — allowed
        content = py_file.read_text()
        if "/workspace/brain" in content:
            violations.append(str(py_file.relative_to(REPO_ROOT)))
    assert not violations, (
        f"Hardcoded /workspace/brain found outside paths.py: {violations}. "
        "Import from engine.paths instead."
    )


def test_paths_module_exports_expected_symbols():
    """engine/paths.py must export BRAIN_ROOT, INDEX_ROOT, DB_PATH, BRAIN_SUBDIRS."""
    sys.path.insert(0, str(REPO_ROOT))
    from engine.paths import BRAIN_ROOT, INDEX_ROOT, DB_PATH, BRAIN_SUBDIRS
    assert isinstance(BRAIN_ROOT, Path)
    assert isinstance(INDEX_ROOT, Path)
    assert isinstance(DB_PATH, Path)
    assert isinstance(BRAIN_SUBDIRS, list)
    assert len(BRAIN_SUBDIRS) == 11
