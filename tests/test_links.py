"""Tests for engine/links.py — backlink maintenance and orphan checking."""
import sqlite3
import pytest
from pathlib import Path


def _init_conn() -> sqlite3.Connection:
    from engine.db import init_schema
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    return conn


def test_add_backlink_appended(tmp_path):
    """add_backlinks appends [[meeting_path]] to alice-smith.md."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    people_dir = brain_root / "people"
    people_dir.mkdir(parents=True)

    person_file = people_dir / "alice-smith.md"
    person_file.write_text("---\ntitle: Alice Smith\n---\n", encoding="utf-8")

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    add_backlinks(meeting_path, ["alice smith"], brain_root, conn)

    text = person_file.read_text(encoding="utf-8")
    assert f"[[{meeting_path}]]" in text


def test_add_backlink_idempotent(tmp_path):
    """Calling add_backlinks twice with same meeting_path appends backlink exactly once."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    people_dir = brain_root / "people"
    people_dir.mkdir(parents=True)

    person_file = people_dir / "alice-smith.md"
    person_file.write_text("---\ntitle: Alice Smith\n---\n", encoding="utf-8")

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    add_backlinks(meeting_path, ["alice smith"], brain_root, conn)
    add_backlinks(meeting_path, ["alice smith"], brain_root, conn)

    text = person_file.read_text(encoding="utf-8")
    assert text.count(f"[[{meeting_path}]]") == 1


def test_relationship_row_inserted(tmp_path):
    """add_backlinks inserts a row into the relationships table."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    people_dir = brain_root / "people"
    people_dir.mkdir(parents=True)

    person_file = people_dir / "alice-smith.md"
    person_file.write_text("---\ntitle: Alice Smith\n---\n", encoding="utf-8")

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    add_backlinks(meeting_path, ["alice smith"], brain_root, conn)

    rows = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships"
    ).fetchall()
    assert len(rows) == 1
    source_path, target_path, rel_type = rows[0]
    assert source_path == str(person_file)
    assert target_path == str(meeting_path)
    assert rel_type == "backlink"


def test_missing_person_skipped(tmp_path):
    """add_backlinks silently skips when person file does not exist."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    (brain_root / "people").mkdir(parents=True)

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    result = add_backlinks(meeting_path, ["bob nobody"], brain_root, conn)
    assert result is None


def test_orphan_missing_target(tmp_path):
    """check_links returns orphan with issue='target missing' when target file absent."""
    from engine.links import check_links

    brain_root = tmp_path / "brain"
    brain_root.mkdir(parents=True)

    source_file = tmp_path / "source.md"
    source_file.write_text("# Source", encoding="utf-8")

    target_path = tmp_path / "missing-target.md"  # does not exist

    conn = _init_conn()
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type, created_at)"
        " VALUES (?, ?, ?, ?)",
        (str(source_file), str(target_path), "backlink", "2026-03-14T00:00:00Z"),
    )
    conn.commit()

    orphans = check_links(brain_root, conn)
    assert len(orphans) == 1
    assert orphans[0]["issue"] == "target missing"
    assert orphans[0]["target"] == str(target_path)


def test_no_orphans_clean_brain(tmp_path):
    """check_links returns [] when both source and target files exist and reference each other."""
    from engine.links import check_links

    brain_root = tmp_path / "brain"
    brain_root.mkdir(parents=True)

    source_file = tmp_path / "alice-smith.md"
    target_file = tmp_path / "2026-03-14-standup.md"

    # target references source in its text
    target_file.write_text(f"# Standup\n[[{source_file}]]", encoding="utf-8")
    # source references target (backlink check: target_text must reference source)
    source_file.write_text(f"# Alice\n[[{target_file}]]", encoding="utf-8")

    conn = _init_conn()
    conn.execute(
        "INSERT INTO relationships (source_path, target_path, rel_type, created_at)"
        " VALUES (?, ?, ?, ?)",
        (str(source_file), str(target_file), "backlink", "2026-03-14T00:00:00Z"),
    )
    conn.commit()

    orphans = check_links(brain_root, conn)
    assert orphans == []


def test_cli_no_orphans(tmp_path, monkeypatch, capsys):
    """main_check_links prints 'No orphaned links found.' when brain is clean."""
    import sqlite3 as _sqlite3
    import engine.db as db_module
    import engine.paths as paths_module
    from engine.links import main_check_links

    mock_conn = _sqlite3.connect(":memory:")
    from engine.db import init_schema
    init_schema(mock_conn)

    monkeypatch.setattr(db_module, "get_connection", lambda: mock_conn)
    monkeypatch.setattr(db_module, "init_schema", lambda conn: None)
    monkeypatch.setattr(paths_module, "BRAIN_ROOT", tmp_path)

    main_check_links()
    captured = capsys.readouterr()
    assert "No orphaned links" in captured.out


@pytest.mark.xfail(strict=False, reason="templates created in plan 04-03")
def test_work_templates_exist():
    """Work templates exist with correct section headers."""
    people_tmpl = Path("brain/.meta/templates/people.md")
    strategy_tmpl = Path("brain/.meta/templates/strategy.md")
    projects_tmpl = Path("brain/.meta/templates/projects.md")
    coding_tmpl = Path("brain/.meta/templates/coding.md")

    assert people_tmpl.exists() and "## Meetings & References" in people_tmpl.read_text()
    assert strategy_tmpl.exists() and "## Key Results" in strategy_tmpl.read_text()
    assert projects_tmpl.exists() and "## Key Contacts" in projects_tmpl.read_text()
    assert coding_tmpl.exists() and "## Decision" in coding_tmpl.read_text()
