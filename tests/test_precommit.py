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
    secret_file = tmp_path / "secrets.py"
    secret_file.write_text('ANTHROPIC_API_KEY = "sk-ant-api03-FAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKEFAKE"')
    result = subprocess.run(
        ["detect-secrets", "scan", str(secret_file)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    assert data["results"], "Expected detect-secrets to flag the API key"


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
