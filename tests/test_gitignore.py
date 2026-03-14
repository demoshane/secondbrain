import pathlib

REPO_ROOT = pathlib.Path(__file__).parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"


def test_env_host_ignored():
    content = GITIGNORE.read_text()
    assert ".env.host" in content, ".gitignore must contain .env.host"


def test_db_files_ignored():
    content = GITIGNORE.read_text()
    assert "*.db" in content, ".gitignore must contain *.db"
