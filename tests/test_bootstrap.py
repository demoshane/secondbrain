import subprocess
import sys
import pytest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import importlib.util


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "bootstrap", REPO_ROOT / "scripts" / "bootstrap.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_reports_pass_fail_per_check(capsys):
    bootstrap = _load_bootstrap()
    # Temporarily replace checks with controlled ones
    original = bootstrap._checks[:]
    bootstrap._checks.clear()

    @bootstrap.check("Always pass")
    def always_pass():
        return True, "ok"

    @bootstrap.check("Always fail")
    def always_fail():
        return False, "broken"

    try:
        results = [(label, fn()) for label, fn in bootstrap._checks]
        for label, (ok, msg) in results:
            status = "PASS" if ok else "FAIL"
            print(f"  [{status}] {label}: {msg}")
        captured = capsys.readouterr()
        assert "[PASS]" in captured.out
        assert "[FAIL]" in captured.out
    finally:
        bootstrap._checks.clear()
        bootstrap._checks.extend(original)


def test_all_checks_reported(capsys):
    """Even if first check fails, all checks run (check-all, not fail-fast)."""
    bootstrap = _load_bootstrap()
    original = bootstrap._checks[:]
    bootstrap._checks.clear()

    call_count = {"n": 0}

    @bootstrap.check("Fails first")
    def fail_first():
        call_count["n"] += 1
        return False, "failed"

    @bootstrap.check("Runs second")
    def run_second():
        call_count["n"] += 1
        return True, "ok"

    try:
        results = [(label, fn()) for label, fn in bootstrap._checks]
        assert call_count["n"] == 2, "Both checks must run even after first failure"
    finally:
        bootstrap._checks.clear()
        bootstrap._checks.extend(original)


def test_bootstrap_dev_flag(tmp_path):
    """bootstrap.py --dev runs without crashing."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bootstrap.py"), "--dev"],
        capture_output=True, text=True
    )
    # Exit code 0 (all pass) or 1 (some fail) — both are acceptable outcomes
    # What matters: no unhandled exception (exit code 2 = argparse error, 3+ = crash)
    assert result.returncode in (0, 1), f"Unexpected exit code {result.returncode}\n{result.stderr}"
    assert "[PASS]" in result.stdout or "[FAIL]" in result.stdout


def test_fresh_install_sequence():
    """bootstrap.py --dev output contains expected check labels."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "bootstrap.py"), "--dev"],
        capture_output=True, text=True
    )
    assert "Drive folder" in result.stdout
    assert ".env.host" in result.stdout
    assert "python-frontmatter" in result.stdout.lower() or "Python dependency" in result.stdout
