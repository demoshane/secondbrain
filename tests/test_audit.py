import pytest


def test_audit_log_create_entry(tmp_path, initialized_db):
    from engine.capture import write_note_atomic, build_post

    target = tmp_path / "note.md"
    post = build_post("note", "Test Note", "Test body", [], [], "public")
    write_note_atomic(target, post, initialized_db)
    rows = initialized_db.execute(
        "SELECT event_type, note_path FROM audit_log WHERE event_type='create'"
    ).fetchall()
    assert len(rows) >= 1
    assert rows[-1][0] == "create"


def test_audit_log_search_entry(seeded_db):
    from engine.search import search_notes

    search_notes(seeded_db, "topic_1")
    rows = seeded_db.execute(
        "SELECT event_type, detail FROM audit_log WHERE event_type='search'"
    ).fetchall()
    assert len(rows) >= 1
    assert rows[-1][0] == "search"
    assert rows[-1][1] == "topic_1"


def test_detect_secrets_baseline_clean():
    import shutil
    import subprocess

    if shutil.which("detect-secrets") is None:
        pytest.skip("detect-secrets not on PATH — run inside DevContainer")

    result = subprocess.run(
        ["detect-secrets", "scan", "--baseline", ".secrets.baseline", "engine/"],
        capture_output=True,
        text=True,
    )
    # Exit code 0 means scan succeeded with no new violations beyond baseline
    assert result.returncode == 0, f"detect-secrets scan failed: {result.stderr}"
