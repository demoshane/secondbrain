"""Backlink maintenance and orphan checker (PEOPLE-03, PEOPLE-04, SEARCH-03)."""
from pathlib import Path
import re
import sqlite3
from engine.db import _now_utc

_WIKI_LINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def extract_wiki_links(body: str) -> list[str]:
    """Return list of paths found inside [[...]] patterns in body.

    Handles both absolute paths ([[/path/to/note.md]]) and relative forms.
    Strips leading/trailing whitespace from each match.
    """
    return [m.strip() for m in _WIKI_LINK_RE.findall(body)]


def update_wiki_link_relationships(
    conn: sqlite3.Connection, source_path: str, body: str
) -> None:
    """Parse wiki-links in body and upsert them into relationships table.

    Deletes all existing wiki-link rows for source_path first (clean-before-insert),
    then inserts a row for each target path found in [[...]] patterns.
    Never raises — DB errors are silently swallowed (best-effort).
    """
    try:
        conn.execute(
            "DELETE FROM relationships WHERE source_path = ? AND rel_type = 'wiki-link'",
            (source_path,),
        )
        targets = extract_wiki_links(body)
        now = _now_utc()
        for target in targets:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (source_path, target, "wiki-link", now),
            )
        conn.commit()
    except Exception:
        pass  # best-effort; never blocks capture or reindex


def ensure_person_profile(
    slug: str, brain_root: Path, conn: sqlite3.Connection | None = None
) -> Path:
    """Return path to an existing or newly-created person note for slug.

    Resolution order:
    1. brain_root/person/{slug}.md already exists → return it (idempotent).
    2. conn provided → search DB for any note with type='person' and matching
       title (case-insensitive). If found, return that file's path so backlinks
       land on the canonical note instead of spawning a duplicate skeleton.
    3. No match → create brain_root/person/{slug}.md with full frontmatter
       (type: person) so it is immediately indexed correctly.
    """
    # Canonical subdirectory is "person/" — confirmed by BRAIN_SUBDIRS in engine/paths.py (F-30).
    person_file = brain_root / "person" / f"{slug}.md"
    if person_file.exists():
        return person_file

    display_name = slug.replace("-", " ").title()

    if conn is not None:
        try:
            row = conn.execute(
                "SELECT path FROM notes WHERE type='person' AND LOWER(title)=LOWER(?)",
                (display_name,),
            ).fetchone()
            if row:
                return brain_root / row[0]
        except Exception:
            pass  # best-effort; fall through to skeleton creation

    person_file.parent.mkdir(parents=True, exist_ok=True)
    now = _now_utc()
    person_file.write_text(
        f"---\ntitle: {display_name}\ntype: person\n"
        f"created_at: '{now}'\nupdated_at: '{now}'\n"
        f"people: []\ntags: []\ncontent_sensitivity: public\n---\n\n",
        encoding="utf-8",
    )
    return person_file


def add_backlinks(
    note_path: Path,
    people: list[str],
    brain_root: Path,
    conn: sqlite3.Connection,
) -> None:
    """Append backlink to each person's profile and record in relationships table.

    People entries can be:
    - Name strings: "Eino Kiiski" → slugified to find/create profile
    - Relative paths: "person/eino-kiiski.md" → resolved directly against brain_root

    - Appends backlink only if not already present (idempotent)
    - Inserts relationships row with INSERT OR IGNORE using relative DB paths (idempotent)
    - Never raises — DB errors are silently swallowed (best-effort)
    """
    from engine.paths import store_path as _store_path

    # Resolve note_path to relative DB path for relationship storage
    try:
        note_db_path = _store_path(note_path.resolve())
    except ValueError:
        note_db_path = str(note_path)

    for person_raw in people:
        person_raw = person_raw.strip()
        # Detect path-format entries (contain / or end with .md)
        if "/" in person_raw or person_raw.endswith(".md"):
            person_file = brain_root / person_raw
            if not person_file.exists():
                # Path doesn't exist — fall back to slug-based resolution
                slug = Path(person_raw).stem.lower().replace(" ", "-")
                person_file = ensure_person_profile(slug, brain_root, conn)
        else:
            slug = person_raw.lower().replace(" ", "-")
            person_file = ensure_person_profile(slug, brain_root, conn)

        # Use relative paths for DB relationship storage
        try:
            person_db_path = _store_path(person_file.resolve())
        except ValueError:
            person_db_path = str(person_file)

        # Skip self-referencing backlinks (person note mentioning itself)
        if person_db_path == note_db_path:
            continue

        text = person_file.read_text(encoding="utf-8")
        # Use relative path for on-disk wiki-links (portable, consistent with DB)
        backlink = f"\n- [[{note_db_path}]]"
        if note_db_path not in text and str(note_path) not in text:
            person_file.write_text(text + backlink, encoding="utf-8")

        try:
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type, created_at)"
                " VALUES (?, ?, ?, ?)",
                (person_db_path, note_db_path, "backlink", _now_utc()),
            )
            conn.commit()
        except Exception:
            pass  # relationship is best-effort; never blocks capture


def traverse_graph(
    conn: sqlite3.Connection,
    start_path: str,
    max_depth: int = 2,
    rel_types: list[str] | None = None,
) -> dict:
    """Multi-hop graph traversal via recursive CTE.

    Returns {"nodes": [...], "edges": [...]} with activation scores decaying
    by depth: strength / (2 ^ depth).  Bidirectional — follows both
    source→target and target→source edges.  Hard cap at 3 hops.
    """
    max_depth = min(max_depth, 3)

    type_filter = ""
    type_params: list = []
    if rel_types:
        placeholders = ",".join("?" for _ in rel_types)
        type_filter = f"AND r.rel_type IN ({placeholders})"
        type_params = list(rel_types)

    # Params must match the positional ? order in the SQL:
    # 1) source_path = ? + type_filter ?s  (base case 1)
    # 2) target_path = ? + type_filter ?s  (base case 2)
    # 3) depth < ? + type_filter ?s        (recursive case)
    params: list = [start_path, *type_params, start_path, *type_params, max_depth, *type_params]

    sql = f"""
    WITH RECURSIVE traverse AS (
        SELECT r.target_path AS path, r.rel_type, COALESCE(r.strength, 1.0) AS strength,
               1 AS depth, r.source_path AS from_path
        FROM relationships r
        WHERE r.source_path = ? {type_filter}
        UNION ALL
        SELECT r.source_path AS path, r.rel_type, COALESCE(r.strength, 1.0) AS strength,
               1 AS depth, r.target_path AS from_path
        FROM relationships r
        WHERE r.target_path = ? {type_filter}
        UNION ALL
        SELECT
            CASE WHEN r.source_path = t.path THEN r.target_path ELSE r.source_path END,
            r.rel_type, COALESCE(r.strength, 1.0), t.depth + 1,
            t.path
        FROM traverse t
        JOIN relationships r ON (r.source_path = t.path OR r.target_path = t.path)
        WHERE t.depth < ? AND
              CASE WHEN r.source_path = t.path THEN r.target_path ELSE r.source_path END != t.from_path
              {type_filter}
    )
    SELECT DISTINCT path, rel_type, strength, depth, from_path FROM traverse
    """

    rows = conn.execute(sql, params).fetchall()

    # Build deduplicated nodes — keep highest activation per path
    node_map: dict[str, dict] = {}
    edges_set: set[tuple[str, str, str]] = set()
    edge_list: list[dict] = []

    # Add start node
    start_row = conn.execute(
        "SELECT title, type FROM notes WHERE path = ?", (start_path,)
    ).fetchone()
    node_map[start_path] = {
        "path": start_path,
        "title": start_row[0] if start_row else start_path.rsplit("/", 1)[-1].replace(".md", ""),
        "note_type": start_row[1] if start_row else "unknown",
        "depth": 0,
        "activation": 1.0,
    }

    for path, rel_type, strength, depth, from_path in rows:
        activation = strength / (2 ** depth)
        if path not in node_map or activation > node_map[path]["activation"]:
            row = conn.execute(
                "SELECT title, type FROM notes WHERE path = ?", (path,)
            ).fetchone()
            node_map[path] = {
                "path": path,
                "title": row[0] if row else path.rsplit("/", 1)[-1].replace(".md", ""),
                "note_type": row[1] if row else "unknown",
                "depth": depth,
                "activation": activation,
            }
        # Add edge (deduplicated by source-target-type triple)
        edge_key = (min(from_path, path), max(from_path, path), rel_type)
        if edge_key not in edges_set:
            edges_set.add(edge_key)
            edge_list.append({
                "source": from_path,
                "target": path,
                "type": rel_type,
                "strength": strength,
            })

    return {"nodes": list(node_map.values()), "edges": edge_list}


def find_path(
    conn: sqlite3.Connection,
    source_path: str,
    target_path: str,
    max_depth: int = 3,
) -> list[dict] | None:
    """Find shortest path between two notes via BFS over relationships.

    Returns list of nodes along the path, or None if no path exists within
    max_depth hops.  Hard cap at 3 hops.
    """
    max_depth = min(max_depth, 3)
    if source_path == target_path:
        row = conn.execute("SELECT title, type FROM notes WHERE path = ?", (source_path,)).fetchone()
        return [{"path": source_path, "title": row[0] if row else source_path, "depth": 0}]

    # BFS
    visited: set[str] = {source_path}
    parent: dict[str, str] = {}
    frontier = [source_path]

    for depth in range(1, max_depth + 1):
        next_frontier: list[str] = []
        for node in frontier:
            neighbors = conn.execute(
                "SELECT target_path FROM relationships WHERE source_path = ? "
                "UNION SELECT source_path FROM relationships WHERE target_path = ?",
                (node, node),
            ).fetchall()
            for (neighbor,) in neighbors:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                parent[neighbor] = node
                if neighbor == target_path:
                    # Reconstruct path
                    path_nodes = []
                    current = target_path
                    while current in parent:
                        row = conn.execute(
                            "SELECT title, type FROM notes WHERE path = ?", (current,)
                        ).fetchone()
                        path_nodes.append({
                            "path": current,
                            "title": row[0] if row else current,
                            "depth": len(path_nodes),
                        })
                        current = parent[current]
                    # Add source
                    row = conn.execute(
                        "SELECT title, type FROM notes WHERE path = ?", (source_path,)
                    ).fetchone()
                    path_nodes.append({
                        "path": source_path,
                        "title": row[0] if row else source_path,
                        "depth": len(path_nodes),
                    })
                    path_nodes.reverse()
                    # Fix depth numbering
                    for i, n in enumerate(path_nodes):
                        n["depth"] = i
                    return path_nodes
                next_frontier.append(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    return None


def check_links(brain_root: Path, conn: sqlite3.Connection) -> list[dict]:
    """Return list of orphan dicts {source, target, issue} from relationships table."""
    orphans = []
    rows = conn.execute(
        "SELECT source_path, target_path, rel_type FROM relationships"
    ).fetchall()
    for source_str, target_str, rel_type in rows:
        # DB stores relative paths — resolve against brain_root for disk access
        source = brain_root / source_str
        target = brain_root / target_str
        if not source.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "source missing"})
            continue
        if not target.exists():
            orphans.append({"source": source_str, "target": target_str, "issue": "target missing"})
    return orphans


def main_check_links() -> None:
    """CLI entry point for sb-check-links."""
    from engine.db import get_connection, init_schema
    from engine.paths import BRAIN_ROOT
    conn = get_connection()
    init_schema(conn)
    orphans = check_links(BRAIN_ROOT, conn)
    conn.close()
    if not orphans:
        print("No orphaned links found.")
        return
    print(f"Found {len(orphans)} orphaned link(s):")
    for o in orphans:
        print(f"  {o['source']} -> {o['target']}: {o['issue']}")
