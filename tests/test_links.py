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
    people_dir = brain_root / "person"
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
    people_dir = brain_root / "person"
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
    people_dir = brain_root / "person"
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
    """add_backlinks silently skips when person file does not exist — legacy behaviour replaced by auto-create."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    (brain_root / "person").mkdir(parents=True)

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    result = add_backlinks(meeting_path, ["bob nobody"], brain_root, conn)
    # Now the profile is created instead of skipped
    assert (brain_root / "person" / "bob-nobody.md").exists()


def test_ensure_person_profile_creates_skeleton(tmp_path):
    """ensure_person_profile creates file with name heading and Backlinks section when absent."""
    from engine.links import ensure_person_profile

    brain_root = tmp_path / "brain"
    (brain_root / "person").mkdir(parents=True)

    path = ensure_person_profile("alice-smith", brain_root)

    assert path == brain_root / "person" / "alice-smith.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "title: Alice Smith" in text


def test_ensure_person_profile_idempotent(tmp_path):
    """ensure_person_profile does not overwrite an existing file."""
    from engine.links import ensure_person_profile

    brain_root = tmp_path / "brain"
    (brain_root / "person").mkdir(parents=True)

    person_file = brain_root / "person" / "alice-smith.md"
    original = "# Alice Smith\n\nExisting content.\n"
    person_file.write_text(original, encoding="utf-8")

    path = ensure_person_profile("alice-smith", brain_root)

    assert path == person_file
    assert person_file.read_text(encoding="utf-8") == original


def test_add_backlinks_creates_profile_when_missing(tmp_path):
    """add_backlinks creates person profile when none exists, then appends backlink."""
    from engine.links import add_backlinks

    brain_root = tmp_path / "brain"
    (brain_root / "person").mkdir(parents=True)

    meeting_path = brain_root / "meeting" / "2026-03-14-standup.md"

    conn = _init_conn()
    add_backlinks(meeting_path, ["charlie brown"], brain_root, conn)

    person_file = brain_root / "person" / "charlie-brown.md"
    assert person_file.exists()
    text = person_file.read_text(encoding="utf-8")
    assert "title: Charlie Brown" in text
    assert f"[[{meeting_path}]]" in text


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


def test_extract_wiki_links_absolute_paths():
    """extract_wiki_links returns list of absolute paths from [[...]] patterns."""
    from engine.links import extract_wiki_links

    body = "See [[/Users/brain/people/alice.md]] and [[/Users/brain/meetings/standup.md]]."
    result = extract_wiki_links(body)
    assert result == ["/Users/brain/people/alice.md", "/Users/brain/meetings/standup.md"]


def test_extract_wiki_links_empty_body():
    """extract_wiki_links returns [] for body with no wiki-links."""
    from engine.links import extract_wiki_links
    assert extract_wiki_links("No links here.") == []


def test_extract_wiki_links_strips_whitespace():
    """extract_wiki_links strips whitespace from matched paths."""
    from engine.links import extract_wiki_links
    assert extract_wiki_links("[[ /path/note.md ]]") == ["/path/note.md"]


def test_update_wiki_link_relationships_inserts_rows(tmp_path):
    """update_wiki_link_relationships writes one row per wiki-link target."""
    import sqlite3
    from engine.db import init_schema
    from engine.links import update_wiki_link_relationships

    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    source = str(tmp_path / "note.md")
    body = "Links: [[/brain/people/alice.md]] and [[/brain/coding/project.md]]"
    update_wiki_link_relationships(conn, source, body)

    rows = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships ORDER BY target_path"
    ).fetchall()
    assert len(rows) == 2
    assert rows[0] == (source, "/brain/coding/project.md", "wiki-link")
    assert rows[1] == (source, "/brain/people/alice.md", "wiki-link")


def test_update_wiki_link_relationships_cleans_stale(tmp_path):
    """update_wiki_link_relationships removes old wiki-link rows before inserting new ones."""
    import sqlite3
    from engine.db import init_schema
    from engine.links import update_wiki_link_relationships

    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    source = str(tmp_path / "note.md")
    # First call with two targets
    update_wiki_link_relationships(conn, source, "[[/brain/a.md]] [[/brain/b.md]]")
    count_before = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert count_before == 2

    # Second call with only one target — stale /brain/b.md row must be removed
    update_wiki_link_relationships(conn, source, "[[/brain/a.md]]")
    rows = conn.execute(
        "SELECT target_path FROM relationships WHERE source_path = ?", (source,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "/brain/a.md"


def test_update_wiki_link_relationships_idempotent(tmp_path):
    """Calling update_wiki_link_relationships twice produces only one row per target."""
    import sqlite3
    from engine.db import init_schema
    from engine.links import update_wiki_link_relationships

    conn = sqlite3.connect(":memory:")
    init_schema(conn)

    source = str(tmp_path / "note.md")
    body = "[[/brain/people/alice.md]]"
    update_wiki_link_relationships(conn, source, body)
    update_wiki_link_relationships(conn, source, body)

    count = conn.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
    assert count == 1


def test_reindex_populates_wiki_link_relationships(tmp_path):
    """reindex_brain creates wiki-link relationship rows for notes with [[...]] links."""
    import sqlite3
    from engine.db import init_schema
    from engine.reindex import reindex_brain

    brain_root = tmp_path / "brain"
    brain_root.mkdir()

    target_note = brain_root / "people" / "alice.md"
    target_note.parent.mkdir()
    target_note.write_text("---\ntype: people\ntitle: Alice\n---\nAlice Smith.", encoding="utf-8")

    source_note = brain_root / "meetings" / "standup.md"
    source_note.parent.mkdir()
    target_rel = "people/alice.md"
    source_note.write_text(
        f"---\ntype: meeting\ntitle: Standup\n---\nSee [[{target_rel}]].",
        encoding="utf-8",
    )

    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    reindex_brain(brain_root, conn)

    rows = conn.execute(
        "SELECT rel_type, target_path FROM relationships WHERE rel_type = 'wiki-link'"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][1] == target_rel


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
