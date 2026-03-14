import json
import shutil
import subprocess
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def test_pre_commit_config_valid():
    cfg = REPO_ROOT / ".pre-commit-config.yaml"
    assert cfg.exists(), ".pre-commit-config.yaml not found"
    content = cfg.read_text()
    assert "detect-secrets" in content
    assert "v1.5.0" in content
    assert ".secrets.baseline" in content


def test_baseline_exists():
    baseline = REPO_ROOT / ".secrets.baseline"
    assert baseline.exists(), ".secrets.baseline not found"
    data = json.loads(baseline.read_text())
    assert "results" in data


@pytest.mark.skipif(shutil.which("detect-secrets") is None, reason="detect-secrets not installed")
def test_blocks_api_key(tmp_path):
    """detect-secrets catches AWS access key pattern AKIA[0-9A-Z]{16}."""
    secret_file = tmp_path / "secrets.py"
    secret_file.write_text('AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"')  # pragma: allowlist secret
    result = subprocess.run(
        ["detect-secrets", "scan", str(secret_file)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    findings = {k: v for k, v in data.get("results", {}).items() if v}
    assert len(findings) > 0, "Expected detect-secrets to flag the AWS access key"


@pytest.mark.skipif(shutil.which("detect-secrets") is None, reason="detect-secrets not installed")
def test_anthropic_key_not_detected(tmp_path):
    """detect-secrets has no Anthropic API key plugin.

    sk-ant-api03-* keys are not detected by pattern matching; protection relies
    on baseline diff for high-entropy values only. This is a known limitation —
    Anthropic key format is not recognised by any built-in detect-secrets plugin
    as of v1.5.0.
    """
    secret_file = tmp_path / "secrets.py"
    secret_file.write_text('ANTHROPIC_API_KEY = "sk-ant-api03-FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE"')
    result = subprocess.run(
        ["detect-secrets", "scan", str(secret_file)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    findings = {k: v for k, v in data.get("results", {}).items() if v}
    assert len(findings) == 0, (
        "detect-secrets unexpectedly flagged an Anthropic key — "
        "a new plugin may have been added; update this test accordingly."
    )


@pytest.mark.skipif(shutil.which("detect-secrets") is None, reason="detect-secrets not installed")
def test_passes_clean_commit(tmp_path):
    clean_file = tmp_path / "clean.py"
    clean_file.write_text('x = 1 + 2\nprint("hello world")\n')
    result = subprocess.run(
        ["detect-secrets", "scan", str(clean_file)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert not data["results"], "Expected no secrets in clean file"
