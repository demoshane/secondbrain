"""Local HTTP sidecar for Second Brain GUI.

Exposes engine functions as HTTP endpoints on 127.0.0.1:37491.
The GUI must call this API only — never import engine modules directly.
"""
import datetime
import json
import mimetypes
import os
import queue
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path
from pathlib import Path as _Path

import frontmatter as _fm
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from engine.db import PERSON_TYPES, PERSON_TYPES_PH, _escape_like, get_connection
from engine.paths import BRAIN_ROOT
from engine.paths import BRAIN_ROOT, store_path
from engine.search import search_notes, _apply_filters
from engine.intelligence import list_actions
from engine.watcher import suppress_next_delete


def _note_folder(path: str) -> str:
    """Derive the subfolder name from a note path (absolute or relative).

    Returns the first directory component relative to BRAIN_ROOT,
    or 'other' if the note is at the root level.
    """
    try:
        p = Path(path)
        rel = p.relative_to(BRAIN_ROOT) if p.is_absolute() else p
        parts = rel.parts
        return parts[0] if len(parts) > 1 else "other"
    except (ValueError, IndexError):
        return "other"

ALLOWED_MIMES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/plain', 'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'image/bmp', 'image/tiff',
}

_STATIC_DIR = _Path(__file__).parent / "gui" / "static"

# Startup health state — populated by startup(), read by /health
_startup_warnings: list[str] = []

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*", "chrome-extension://*"])


@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({"error": "File too large (max 50 MB)"}), 413


# ---------------------------------------------------------------------------
# SSE subscriber registry
# ---------------------------------------------------------------------------

_subscribers: list[queue.Queue] = []
_subscribers_lock = threading.Lock()


def _subscribe() -> queue.Queue:
    q: queue.Queue = queue.Queue(maxsize=50)
    with _subscribers_lock:
        _subscribers.append(q)
    return q


def _unsubscribe(q: queue.Queue) -> None:
    with _subscribers_lock:
        if q in _subscribers:
            _subscribers.remove(q)


def _broadcast(event: dict) -> None:
    payload = f"event: note\ndata: {json.dumps(event)}\n\n"
    with _subscribers_lock:
        for q in list(_subscribers):
            try:
                q.put_nowait(payload)
            except queue.Full:
                pass


@app.get("/events")
def event_stream():
    from flask import Response, stream_with_context
    q = _subscribe()

    def generate():
        try:
            while True:
                try:
                    data = q.get(timeout=15)
                    yield data
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            _unsubscribe(q)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def start_note_observer():
    """Start a watchdog observer for the brain directory; broadcast note changes via SSE."""
    from watchdog.observers import Observer
    from engine.watcher import NoteChangeHandler
    brain_root = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    handler = NoteChangeHandler(_broadcast)
    obs = Observer()
    obs.schedule(handler, brain_root, recursive=True)
    obs.daemon = True
    obs.start()
    return obs


@app.get("/health")
def health():
    return jsonify({"status": "ok", "port": 37491, "warnings": _startup_warnings})


@app.get("/ping")
def ping():
    return jsonify({"ok": True})


@app.post("/notes/refresh")
def notes_refresh():
    """Notify all SSE subscribers to reload the notes list.

    Called by sb-watch after capturing a new file, since cross-process
    filesystem events (FSEvents coalescing) are not reliable for triggering
    the watchdog observer in the GUI process.
    """
    _broadcast({"type": "created", "path": ""})
    return jsonify({"ok": True})


@app.get("/notes")
def list_notes():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        rows = conn.execute(
            "SELECT path, title, type, created_at, tags FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    notes = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        d["folder"] = _note_folder(d["path"])
        notes.append(d)
    return jsonify({"notes": notes, "total": total, "limit": limit, "offset": offset})


@app.post("/search")
def search():
    body = request.get_json(force=True) or {}
    query = body.get("query", "")
    tags_filter = body.get("tags")  # list[str] | None (backwards compat)
    person = body.get("person")      # str | None
    tag = body.get("tag")            # str | None — single tag filter
    note_type = body.get("note_type")  # str | None
    from_date = body.get("from_date")  # str | None — ISO date YYYY-MM-DD
    to_date = body.get("to_date")      # str | None — ISO date YYYY-MM-DD
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        if tags_filter and not query:
            # Tags-only filter: use note_tags junction table for indexed lookups.
            # Strategy: fetch candidates matching first tag, then Python-filter for the rest.
            # This avoids dynamic SQL (semgrep-safe) while still using the indexed junction table.
            first_tag = tags_filter[0]
            rest_tags = set(tags_filter[1:])
            sql = """
                SELECT n.path, n.type, n.title, n.created_at
                FROM notes n
                WHERE n.path IN (SELECT note_path FROM note_tags WHERE tag=?)
                ORDER BY n.created_at DESC
            """
            rows = conn.execute(sql, (first_tag,)).fetchall()
            if rest_tags:
                # For each candidate, fetch its tags from junction table and check all required tags present
                filtered_rows = []
                for r in rows:
                    note_tags_rows = conn.execute(
                        "SELECT tag FROM note_tags WHERE note_path=?", (r["path"],)
                    ).fetchall()
                    note_tag_set = {nt["tag"] for nt in note_tags_rows}
                    if rest_tags.issubset(note_tag_set):
                        filtered_rows.append(r)
                rows = filtered_rows
            results = [
                {
                    "path": r["path"],
                    "type": r["type"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "score": 0.0,
                }
                for r in rows
            ]
        else:
            results = search_notes(conn, query)
            if tags_filter:
                # Post-filter FTS results using note_tags junction table (semgrep-safe: no dynamic SQL)
                tags_set = set(tags_filter)
                filtered = []
                for r in results:
                    note_tags_rows = conn.execute(
                        "SELECT tag FROM note_tags WHERE note_path=?", (r["path"],)
                    ).fetchall()
                    note_tag_set = {nt["tag"] for nt in note_tags_rows}
                    if tags_set.issubset(note_tag_set):
                        filtered.append(r)
                results = filtered
        # Apply entity filters (person, tag, note_type, from_date, to_date) — AND logic
        results = _apply_filters(
            results, conn,
            person=person,
            tag=tag,
            note_type=note_type,
            from_date=from_date,
            to_date=to_date,
        )
    finally:
        conn.close()
    for r in results:
        if isinstance(r, dict):
            r["folder"] = _note_folder(r.get("path", ""))
    return jsonify({"results": results})


def _resolve_note_path(note_path: str) -> tuple[Path, Path]:
    """Return (abs_path, brain_root). Raises ValueError if path escapes brain_root."""
    brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))).resolve()
    # Flask <path:> strips the leading '/', so absolute paths arrive without it.
    # Detect by checking if prepending '/' yields a path inside brain_root.
    if note_path.startswith("/"):
        p = Path(note_path).resolve()
    elif Path("/" + note_path).resolve().is_relative_to(brain_root):
        p = Path("/" + note_path).resolve()
    else:
        p = (brain_root / note_path).resolve()
    if not p.is_relative_to(brain_root):
        raise ValueError("path traversal")
    return p, brain_root


@app.get("/notes/<path:note_path>")
def read_note(note_path):
    try:
        p, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    raw = p.read_text(encoding="utf-8")
    if request.args.get("raw"):
        return jsonify({"content": raw, "path": str(p)})
    post = _fm.loads(raw)
    meta = post.metadata or {}
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        import json as _json
        try:
            tags = _json.loads(tags)
        except Exception:
            tags = []
    return jsonify({
        "body": post.content,
        "path": str(p),
        "title": meta.get("title", p.stem),
        "type": meta.get("type", "note"),
        "tags": tags,
    })


@app.get("/persons")
@app.get("/people")  # deprecated alias
def list_people():
    from engine.people import list_people_with_metrics
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    conn = get_connection()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM notes WHERE type IN ({PERSON_TYPES_PH})", PERSON_TYPES
        ).fetchone()[0]
        result = list_people_with_metrics(conn)
    finally:
        conn.close()
    paginated = result[offset:offset + limit]
    return jsonify({"people": paginated, "total": total, "limit": limit, "offset": offset})


@app.get("/meetings")
def list_meetings():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE type = 'meeting'"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT n.path, n.title, substr(n.created_at,1,10) AS meeting_date, n.people, "
            "  (SELECT COUNT(*) FROM action_items a WHERE a.note_path=n.path AND a.done=0) AS open_actions "
            "FROM notes n WHERE n.type = 'meeting' ORDER BY n.created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        try:
            participants = json.loads(r["people"] or "[]")
        except Exception:
            participants = []
        result.append({
            "path": r["path"],
            "title": r["title"] or "",
            "meeting_date": r["meeting_date"] or "",
            "participant_count": len(participants),
            "open_actions": r["open_actions"] or 0,
        })
    return jsonify({"meetings": result, "total": total, "limit": limit, "offset": offset})


@app.get("/meetings/<path:note_path>")
def get_meeting(note_path):
    try:
        abs_path, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, body, people, substr(created_at,1,10) AS meeting_date FROM notes WHERE path=?",
            (store_path(abs_path),)
        ).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        try:
            participants = json.loads(row["people"] or "[]")
        except Exception:
            participants = []
        open_actions = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE note_path=? AND done=0",
            (store_path(abs_path),)
        ).fetchone()[0]
    finally:
        conn.close()
    return jsonify({
        "path": row["path"],
        "title": row["title"] or "",
        "body": row["body"] or "",
        "meeting_date": row["meeting_date"] or "",
        "participants": participants,
        "open_actions": open_actions,
    })


@app.get("/projects")
def list_projects():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE type = 'projects'"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT n.path, n.title, substr(n.updated_at,1,10) AS updated_at, "
            "  (SELECT COUNT(*) FROM action_items a WHERE a.note_path=n.path AND a.done=0) AS open_actions "
            "FROM notes n WHERE n.type = 'projects' ORDER BY n.updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"projects": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset})


@app.get("/projects/<path:note_path>")
def get_project(note_path):
    try:
        abs_path, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, body, substr(updated_at,1,10) AS updated_at FROM notes WHERE path=?",
            (store_path(abs_path),)
        ).fetchone()
        if row is None:
            return jsonify({"error": "not found"}), 404
        open_actions = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE note_path=? AND done=0",
            (store_path(abs_path),)
        ).fetchone()[0]
    finally:
        conn.close()
    return jsonify({
        "path": row["path"],
        "title": row["title"] or "",
        "body": row["body"] or "",
        "updated_at": row["updated_at"] or "",
        "open_actions": open_actions,
    })


@app.post("/persons")
@app.post("/people")  # deprecated alias
def create_person():
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    role = data.get("role", "").strip()
    body = f"Role: {role}" if role else ""
    from engine.capture import capture_note
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
        brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))
        result_path = capture_note(
            note_type="person",
            title=name,
            body=body,
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=brain_root,
            conn=conn,
        )
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"path": str(result_path)}), 201


@app.post("/meetings")
def create_meeting():
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    from engine.capture import capture_note
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
        brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))
        result_path = capture_note(
            note_type="meeting",
            title=name,
            body="",
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=brain_root,
            conn=conn,
        )
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"path": str(result_path)}), 201


@app.post("/projects")
def create_project():
    data = request.get_json(force=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    from engine.capture import capture_note
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
        brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))
        result_path = capture_note(
            note_type="projects",
            title=name,
            body="",
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=brain_root,
            conn=conn,
        )
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"path": str(result_path)}), 201


@app.get("/persons/<path:note_path>/links")
@app.get("/people/<path:note_path>/links")  # deprecated alias
def get_person_links(note_path):
    try:
        abs_path, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    path_str = store_path(abs_path)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        # Resolve person title from DB so we can match note_people by name/slug
        row = conn.execute("SELECT title FROM notes WHERE path = ?", (path_str,)).fetchone()
        title = row["title"] if row else ""
        slug = abs_path.stem  # filename without .md
        # note_people.person stores names or slugs — check all variants
        variants = list({path_str, title, slug})
        placeholders = ",".join("?" * len(variants))
        mention_count = conn.execute(
            f"SELECT COUNT(DISTINCT note_path) FROM note_people WHERE person IN ({placeholders})",
            variants,
        ).fetchone()[0]
        action_count = conn.execute(
            f"SELECT COUNT(*) FROM action_items WHERE assignee_path IN ({placeholders}) AND done = 0",
            variants,
        ).fetchone()[0]
    finally:
        conn.close()
    return jsonify({"meeting_count": mention_count, "action_count": action_count})


@app.delete("/persons/<path:note_path>")
@app.delete("/people/<path:note_path>")  # deprecated alias
def delete_person(note_path):
    try:
        abs_path, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    path_str = store_path(abs_path)
    conn = get_connection()
    try:
        # Clear assignee references before delete (avoids orphan FK refs)
        conn.execute(
            "UPDATE action_items SET assignee_path = NULL WHERE assignee_path = ?",
            (path_str,)
        )
        # Remove from note_people junction (person column stores path or name)
        conn.execute("DELETE FROM note_people WHERE person = ?", (path_str,))
        conn.commit()
        from engine.delete import delete_note
        result = delete_note(abs_path, conn, brain_root)
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify(result), 200


@app.delete("/meetings/<path:note_path>")
def delete_meeting(note_path):
    try:
        abs_path, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    try:
        from engine.delete import delete_note
        result = delete_note(abs_path, conn, brain_root)
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify(result), 200


@app.delete("/projects/<path:note_path>")
def delete_project(note_path):
    try:
        abs_path, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    try:
        from engine.delete import delete_note
        result = delete_note(abs_path, conn, brain_root)
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify(result), 200


@app.get("/links")
def list_links():
    from urllib.parse import urlparse
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total_count = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE type='link'"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT path, title, url, substr(created_at,1,10) AS date, tags, "
            "  substr(body,1,200) AS description "
            "FROM notes WHERE type='link' ORDER BY created_at DESC "
            "LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        domain = ""
        if r["url"]:
            parsed = urlparse(r["url"])
            domain = parsed.hostname or ""
        result.append({
            "path": r["path"],
            "title": r["title"] or "",
            "url": r["url"] or "",
            "domain": domain,
            "date": r["date"] or "",
            "tags": json.loads(r["tags"] or "[]"),
            "description": r["description"] or "",
        })
    return jsonify({"links": result, "total": total_count})


@app.get("/links/<path:note_path>")
def get_link(note_path):
    from urllib.parse import urlparse
    try:
        abs_path, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, url, body, substr(created_at,1,10) AS date, tags "
            "FROM notes WHERE path=? AND type='link'",
            (store_path(abs_path),)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    domain = ""
    if row["url"]:
        parsed = urlparse(row["url"])
        domain = parsed.hostname or ""
    return jsonify({
        "path": row["path"],
        "title": row["title"] or "",
        "url": row["url"] or "",
        "domain": domain,
        "body": row["body"] or "",
        "date": row["date"] or "",
        "tags": json.loads(row["tags"] or "[]"),
    })


@app.get("/tags")
def list_tags():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT tag FROM note_tags ORDER BY tag"
        ).fetchall()
        tags = [r[0] for r in rows]
        if not tags:
            # Fallback: query JSON tags column if note_tags is empty (per Pitfall 6)
            # MUST be inside the same `with` block — conn is closed after exiting
            fallback_rows = conn.execute(
                "SELECT tags FROM notes WHERE tags IS NOT NULL AND tags != '[]'"
            ).fetchall()
            import json as _json
            tag_set = set()
            for r in fallback_rows:
                try:
                    tag_set.update(_json.loads(r[0]))
                except (_json.JSONDecodeError, TypeError):
                    pass
            tags = sorted(tag_set)
    return jsonify({"tags": tags})


@app.get("/actions")
def get_actions():
    done = request.args.get("done", "0") == "1"
    assignee = request.args.get("assignee") or None
    note_path = request.args.get("note_path") or None
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE done=?", (1 if done else 0,)
        ).fetchone()[0]
        actions = list_actions(conn, done=done, assignee=assignee, note_path=note_path)
    finally:
        conn.close()
    # Apply limit/offset in Python (list_actions returns all matching rows)
    paginated = actions[offset:offset + limit]
    return jsonify({"actions": paginated, "total": total, "limit": limit, "offset": offset})


_PREFS_FILE = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))) / ".sb-gui-prefs.json"


def _get_prefs_path() -> _Path:
    """Return the prefs file path, resolved at call time to respect BRAIN_PATH changes in tests."""
    brain = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    return _Path(brain) / ".sb-gui-prefs.json"


@app.get("/ui/prefs")
def get_prefs():
    p = _get_prefs_path()
    if p.exists():
        try:
            return jsonify(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jsonify({})


@app.put("/ui/prefs")
def put_prefs():
    data = request.get_json(force=True) or {}
    p = _get_prefs_path()
    try:
        p.write_text(json.dumps(data), encoding="utf-8")
        return jsonify({"saved": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/ui")
def gui_shell():
    html = (_STATIC_DIR / "index.html").read_text(encoding="utf-8")
    api_base = request.host_url.rstrip("/")
    injection = f'<script>window.API_BASE = "{api_base}";</script>'
    html = html.replace("</head>", injection + "\n</head>", 1)
    return html


@app.get("/ui/<path:filename>")
def gui_static(filename):
    import flask
    return flask.send_from_directory(str(_STATIC_DIR), filename)


@app.put("/notes/<path:note_path>")
def save_note(note_path):
    try:
        p, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(force=True) or {}

    # Title-only branch: when "title" present and "content"/"tags" absent
    title_val = body.get("title")
    if title_val is not None and "content" not in body and "tags" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["title"] = title_val
        updated_text = _fm.dumps(post)
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
            f.write(updated_text)
            tmp = f.name
        suppress_next_delete(str(p))
        os.replace(tmp, p)
        now = datetime.datetime.utcnow().isoformat()
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE notes SET title=?, updated_at=? WHERE path=?",
                (title_val, now, store_path(p))
            )
            conn.commit()
        finally:
            conn.close()
        return jsonify({"saved": True, "path": str(p)})

    # Body-only branch: when "body" present and "content"/"tags"/"title" absent
    body_val = body.get("body")
    if body_val is not None and "content" not in body and "tags" not in body and "title" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.content = body_val
        updated_text = _fm.dumps(post)
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
            f.write(updated_text)
            tmp = f.name
        suppress_next_delete(str(p))
        os.replace(tmp, p)
        now = datetime.datetime.utcnow().isoformat()
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE notes SET body=?, updated_at=? WHERE path=?",
                (body_val, now, store_path(p))
            )
            conn.commit()
        finally:
            conn.close()
        return jsonify({"saved": True, "path": str(p)})

    # Tags-only branch: when "tags" present and "content" absent, update frontmatter + DB only
    tags_val = body.get("tags")
    if tags_val is not None and "content" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["tags"] = tags_val
        updated_text = _fm.dumps(post)
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
            f.write(updated_text)
            tmp = f.name
        suppress_next_delete(str(p))
        os.replace(tmp, p)
        now = datetime.datetime.utcnow().isoformat()
        conn = get_connection()
        try:
            conn.execute(
                "UPDATE notes SET tags=?, updated_at=? WHERE path=?",
                (json.dumps(tags_val), now, store_path(p))
            )
            conn.commit()
        finally:
            conn.close()
        return jsonify({"saved": True, "path": str(p)})

    content = body.get("content", "")
    with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    suppress_next_delete(str(p))
    os.replace(tmp, p)
    saved_text = p.read_text(encoding="utf-8")
    post = _fm.loads(saved_text)
    title = post.metadata.get("title", p.stem)
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE notes SET title=?, updated_at=? WHERE path=?",
            (title, now, store_path(p))
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"saved": True, "path": str(p)})


VALID_NOTE_TYPES = {
    "note", "meeting", "person", "idea", "link",
    "project", "coding", "strategy", "personal", "files",
}


@app.post("/notes")
def create_note():
    body = request.get_json(force=True) or {}
    title = body.get("title", "untitled")
    note_type = body.get("type", "idea")
    note_body = body.get("body", "")
    brain_path = body.get("brain_path", "") or str(BRAIN_ROOT)
    source_url = body.get("source_url", "")
    if note_type not in VALID_NOTE_TYPES:
        return jsonify({"error": f"invalid note type: {note_type!r}"}), 400
    import datetime
    slug = datetime.date.today().isoformat() + "-" + title[:40].replace(" ", "-").lower()
    subdir = "ideas" if note_type == "idea" else note_type
    brain_root = _Path(brain_path).resolve()
    target = brain_root / subdir / f"{slug}.md"
    # Resolve slug collision: append a counter if the target already exists
    if target.exists():
        counter = 1
        while target.exists():
            target = brain_root / subdir / f"{slug}-{counter}.md"
            counter += 1
    # Path-confinement check: ensure target is inside the declared brain directory
    if not target.resolve().is_relative_to(brain_root):
        return jsonify({"error": "Forbidden"}), 403
    target.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.date.today().isoformat()
    url_line = f"url: {source_url}\n" if source_url else ""
    md_content = (
        f"---\ntype: {note_type}\ntitle: {title}\ndate: {today}\n"
        f"tags: []\npeople: []\ncreated_at: {now}\nupdated_at: {now}\n"
        f"content_sensitivity: public\n{url_line}---\n\n{note_body}\n"
    )
    target.write_text(md_content, encoding="utf-8")
    # Index the new note into SQLite immediately so loadNotes() reflects it
    abs_path = str(target.resolve())
    rel_path = str(target.resolve().relative_to(brain_root))
    conn = get_connection()
    try:
        existing = conn.execute("SELECT path FROM notes WHERE path=?", (rel_path,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO notes (path, title, type, body, tags, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (rel_path, title, note_type, note_body, "[]", now, now),
            )
            conn.commit()
    finally:
        conn.close()
    return jsonify({"path": abs_path}), 201


@app.delete("/notes/<path:note_path>")
def delete_note_endpoint(note_path):
    try:
        p, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    from engine.delete import delete_note  # lazy import
    conn = get_connection()
    try:
        result = delete_note(p, conn, brain_root)
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500
    finally:
        conn.close()
    return jsonify(result), 200


@app.get("/notes/<path:note_path>/meta")
def note_meta(note_path):
    try:
        p, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        db_path = store_path(p)
        title_row = conn.execute(
            "SELECT title FROM notes WHERE path=?", (db_path,)
        ).fetchone()
        if title_row and title_row["title"]:
            rows = conn.execute(
                "SELECT path, title FROM notes "
                "WHERE path != ? AND LOWER(body) LIKE LOWER(?)",
                (db_path, f"%{title_row['title']}%"),
            ).fetchall()
            backlinks = [dict(r) for r in rows]
        else:
            backlinks = []
        related = []
        if title_row:
            related_rows = search_notes(conn, title_row["title"])
            related = [r for r in related_rows if r.get("path") != db_path][:5]
        note_row = conn.execute(
            "SELECT people, body FROM notes WHERE path=?", (db_path,)
        ).fetchone()
        raw_people = json.loads(note_row["people"]) if note_row and note_row["people"] else []
        note_body = note_row["body"] if note_row else ""

        # Resolve raw_people entries — may be paths (absolute or relative) OR plain name strings.
        # Treat as a path if it contains a path separator or ends with .md.
        people = []
        seen_paths = set()
        for item in raw_people:
            item_str = str(item)
            is_path = "/" in item_str or item_str.endswith(".md")
            if is_path:
                # Normalise to relative for DB lookup
                try:
                    lookup_path = store_path(_Path(item_str)) if _Path(item_str).is_absolute() else item_str
                except ValueError:
                    lookup_path = item_str
                title_r = conn.execute(
                    "SELECT path, title FROM notes WHERE path=?", (lookup_path,)
                ).fetchone()
                if title_r:
                    if title_r["path"] not in seen_paths:
                        seen_paths.add(title_r["path"])
                        people.append({"path": title_r["path"], "title": title_r["title"]})
                else:
                    # Path not in DB — derive display title from stem
                    if lookup_path not in seen_paths:
                        seen_paths.add(lookup_path)
                        people.append({
                            "path": lookup_path,
                            "title": _Path(item_str).stem.replace("-", " ").title(),
                        })
            else:
                # Plain name string — look up by title in person notes
                title_r = conn.execute(
                    f"SELECT path, title FROM notes "
                    f"WHERE LOWER(title) = LOWER(?) AND type IN ({PERSON_TYPES_PH}) "
                    f"LIMIT 1",
                    (item_str, *PERSON_TYPES),
                ).fetchone()
                if title_r:
                    if title_r["path"] not in seen_paths:
                        seen_paths.add(title_r["path"])
                        people.append({"path": title_r["path"], "title": title_r["title"]})
                else:
                    # Name not found as a person note — show as plain label with no path
                    if item_str not in seen_paths:
                        seen_paths.add(item_str)
                        people.append({"path": None, "title": item_str})
    finally:
        conn.close()
    return jsonify({"backlinks": backlinks, "related": related, "people": people})


@app.get("/files")
def list_files():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    files_dir = _Path(brain_path) / "files"
    all_files = []
    if files_dir.exists():
        for f in sorted(files_dir.rglob("*")):
            if f.is_file():
                all_files.append({
                    "path": str(f),
                    "name": f.name,
                    "rel_path": str(f.relative_to(files_dir)),
                    "size": f.stat().st_size,
                })
    total = len(all_files)
    paginated = all_files[offset:offset + limit]
    return jsonify({"files": paginated, "total": total, "limit": limit, "offset": offset})


@app.get("/files/usages")
def file_usages():
    """Return notes that reference a given file path via the attachments table."""
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"usages": []})
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT a.note_path, COALESCE(n.title, a.note_path) AS title
               FROM attachments a
               LEFT JOIN notes n ON n.path = a.note_path
               WHERE a.file_path = ?""",
            (file_path,),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"usages": [{"note_path": r[0], "title": r[1]} for r in rows]})


@app.delete("/files")
def delete_file():
    """Delete an uploaded file from disk and remove its attachments row.

    JSON body:
        path: absolute path to the file (must be inside BRAIN_PATH/files/).
    """
    body = request.get_json(force=True) or {}
    file_path = body.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    files_dir = _Path(brain_path) / "files"
    target = _Path(file_path).resolve()

    # Path-traversal guard: must be inside files/
    try:
        target.relative_to(files_dir.resolve())
    except ValueError:
        return jsonify({"error": "Path outside files directory"}), 403

    if not target.exists():
        return jsonify({"error": "File not found"}), 404

    target.unlink()

    conn = get_connection()
    try:
        conn.execute("DELETE FROM attachments WHERE file_path = ?", (file_path,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"deleted": True})


@app.post("/files/move")
def move_file():
    body = request.get_json(force=True) or {}
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        return jsonify({"error": "src and dst required"}), 400
    src_p = _Path(src).resolve()
    dst_p = _Path(dst).resolve()
    # ARCH-07: path traversal guard — both src and dst must be within BRAIN_ROOT
    from engine.paths import BRAIN_ROOT
    if not src_p.is_relative_to(BRAIN_ROOT) or not dst_p.is_relative_to(BRAIN_ROOT):
        return jsonify({"error": "Path outside brain directory"}), 403
    if not src_p.exists():
        return jsonify({"error": "src not found"}), 404
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))
    return jsonify({"moved": True, "dst": str(dst_p)})


@app.post("/files/upload")
def upload_file():
    """Receive a file upload, save to files/, record in attachments table.

    Form fields:
        file:      The uploaded file (multipart).
        note_path: The note this attachment belongs to (string).

    Returns 400 if no file or empty filename, 415 if MIME type not allowed.
    """
    from engine.attachments import save_attachment, suppress_next_create

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400

    note_path = request.form.get("note_path", "")

    # MIME check — use supplied content_type first, fall back to guessing from extension
    mime = f.content_type or mimetypes.guess_type(f.filename)[0] or ""
    # Strip charset suffix if present (e.g. "text/plain; charset=utf-8")
    mime = mime.split(";")[0].strip()
    if mime not in ALLOWED_MIMES:
        return jsonify({"error": "Unsupported media type"}), 415

    filename = secure_filename(f.filename)
    if not filename:
        return jsonify({"error": "Invalid filename"}), 400

    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    dest = _Path(brain_path) / "files" / filename

    # Collision handling: append counter suffix before extension
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        counter = 2
        while dest.exists():
            dest = _Path(brain_path) / "files" / f"{stem}-{counter}{suffix}"
            counter += 1

    dest.parent.mkdir(parents=True, exist_ok=True)

    # Suppress watchdog created event BEFORE saving to disk
    suppress_next_create(str(dest))
    f.save(str(dest))

    attachment = save_attachment(note_path, str(dest), dest.name, dest.stat().st_size)
    _broadcast({"type": "attachment", "note_path": note_path})
    return jsonify(attachment), 200


@app.get("/notes/attachments")
def list_note_attachments():
    """Return all attachments associated with a note.

    note_path is a query parameter (?path=...) to avoid %2F encoding issues
    when absolute filesystem paths are passed from the frontend.
    It is used only as a DB lookup key — never to open a file.
    """
    from engine.attachments import list_attachments

    note_path = request.args.get("path", "")
    attachments = list_attachments(note_path)
    return jsonify({"attachments": attachments}), 200


@app.post("/batch-capture")
def batch_capture():
    """Index all untracked .md files in the brain directory into the notes table.

    Walks brain_root rglob("*.md"), skips hidden-directory paths and paths
    already present in the notes table, inserts absent ones, and returns
    {"succeeded": [...], "failed": [...]}.
    """
    import frontmatter as _fm_batch

    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    brain_root = _Path(brain_path)

    conn = get_connection()
    try:
        existing = {
            row[0] for row in conn.execute("SELECT path FROM notes").fetchall()
        }

        succeeded = []
        failed = []

        for md_file in brain_root.rglob("*.md"):
            # Skip hidden directories (any path segment relative to brain_root starting with '.')
            if any(part.startswith(".") for part in md_file.relative_to(brain_root).parts):
                continue

            abs_str = str(md_file.resolve())
            if abs_str in existing:
                continue

            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                post = _fm_batch.loads(text)
                title = post.metadata.get("title", md_file.stem)
                note_type = post.metadata.get("type", "note")
                body = post.content or ""
                now = datetime.datetime.utcnow().isoformat()
                conn.execute(
                    "INSERT INTO notes (path, title, type, body, tags, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (abs_str, title, note_type, body, "[]", now, now),
                )
                succeeded.append({"path": abs_str, "title": title})
            except Exception as exc:
                failed.append({"path": abs_str, "error": str(exc)})

        # Also register any files in files/ not yet tracked in attachments table
        files_dir = brain_root / "files"
        if files_dir.exists():
            tracked_files = {
                row[0] for row in conn.execute("SELECT file_path FROM attachments").fetchall()
            }
            now = datetime.datetime.utcnow().isoformat()
            for f in sorted(files_dir.rglob("*")):
                if not f.is_file():
                    continue
                abs_file = str(f.resolve())
                if abs_file in tracked_files:
                    continue
                try:
                    conn.execute(
                        "INSERT INTO attachments (note_path, file_path, filename, size, uploaded_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        ("", abs_file, f.name, f.stat().st_size, now),
                    )
                    succeeded.append({"path": abs_file, "title": f.name})
                except Exception as exc:
                    failed.append({"path": abs_file, "error": str(exc)})

        conn.commit()
    finally:
        conn.close()

    _broadcast({"type": "created", "path": ""})
    return jsonify({"succeeded": succeeded, "failed": failed}), 200


@app.post("/actions/<int:action_id>/done")
def action_done(action_id):
    conn = get_connection()
    try:
        conn.execute("UPDATE action_items SET done=1 WHERE id=?", (action_id,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"done": True, "id": action_id})


@app.put("/actions/<int:action_id>")
def update_action(action_id):
    """Update action item fields. Supports: assignee_path, done."""
    data = request.get_json(force=True)
    conn = get_connection()
    try:
        if "assignee_path" in data:
            conn.execute(
                "UPDATE action_items SET assignee_path=? WHERE id=?",
                (data["assignee_path"], action_id),
            )
        if "done" in data:
            conn.execute(
                "UPDATE action_items SET done=? WHERE id=?",
                (1 if data["done"] else 0, action_id),
            )
        if "due_date" in data:
            conn.execute(
                "UPDATE action_items SET due_date=? WHERE id=?",
                (data["due_date"], action_id),
            )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"updated": True, "id": action_id})


@app.delete("/actions/<int:action_id>")
def delete_action(action_id):
    """Delete an action item."""
    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM action_items WHERE id=?", (action_id,))
        conn.commit()
        if cur.rowcount == 0:
            return jsonify({"error": "Not found"}), 404
    finally:
        conn.close()
    return jsonify({"deleted": True, "id": action_id})


@app.get("/intelligence")
def get_intelligence():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        from engine.intelligence import get_stale_notes
        try:
            nudge_rows = get_stale_notes(conn, limit=5)
            nudges = nudge_rows if isinstance(nudge_rows, list) else []
        except Exception:
            nudges = []
    finally:
        conn.close()
    return jsonify({"recap": None, "nudges": nudges})


@app.post("/intelligence/recap")
def intelligence_recap():
    """On-demand recap generation. Always regenerates — no idempotency guard."""
    conn = get_connection()
    try:
        from engine.intelligence import generate_recap_on_demand
        text = generate_recap_on_demand(conn)
        return jsonify({"recap": text})
    except Exception as exc:
        return jsonify({"recap": f"Error: {exc}"}), 500
    finally:
        conn.close()


@app.get("/inbox")
def get_inbox():
    """Return inbox items: unassigned actions, unprocessed notes, empty notes."""
    PAGE_SIZE = 20
    actions_offset = int(request.args.get("actions_offset", 0))
    source_note = request.args.get("source_note") or None

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        # --- Unassigned actions ---
        if source_note:
            total_row = conn.execute(
                "SELECT COUNT(*) FROM action_items a "
                "LEFT JOIN dismissed_inbox_items d ON d.path=CAST(a.id AS TEXT) AND d.item_type='action' "
                "WHERE a.done=0 AND a.assignee_path IS NULL AND d.path IS NULL AND a.note_path=?",
                (source_note,),
            ).fetchone()
            action_rows = conn.execute(
                "SELECT a.id, a.note_path, a.text, a.created_at FROM action_items a "
                "LEFT JOIN dismissed_inbox_items d ON d.path=CAST(a.id AS TEXT) AND d.item_type='action' "
                "WHERE a.done=0 AND a.assignee_path IS NULL AND d.path IS NULL AND a.note_path=? "
                "ORDER BY a.created_at DESC LIMIT ? OFFSET ?",
                (source_note, PAGE_SIZE, actions_offset),
            ).fetchall()
        else:
            total_row = conn.execute(
                "SELECT COUNT(*) FROM action_items a "
                "LEFT JOIN dismissed_inbox_items d ON d.path=CAST(a.id AS TEXT) AND d.item_type='action' "
                "WHERE a.done=0 AND a.assignee_path IS NULL AND d.path IS NULL",
            ).fetchone()
            action_rows = conn.execute(
                "SELECT a.id, a.note_path, a.text, a.created_at FROM action_items a "
                "LEFT JOIN dismissed_inbox_items d ON d.path=CAST(a.id AS TEXT) AND d.item_type='action' "
                "WHERE a.done=0 AND a.assignee_path IS NULL AND d.path IS NULL "
                "ORDER BY a.created_at DESC LIMIT ? OFFSET ?",
                (PAGE_SIZE, actions_offset),
            ).fetchall()
        unassigned_actions_total = total_row[0] if total_row else 0
        unassigned_actions = [dict(r) for r in action_rows]

        # --- Unprocessed notes (14-day window, no tags, no relationships, structured types only) ---
        PROCESSABLE_TYPES = ('idea', 'ideas', 'coding', 'strategy', 'personal', 'projects')
        type_placeholders = ",".join("?" * len(PROCESSABLE_TYPES))
        unprocessed_rows = conn.execute(
            f"SELECT n.path, n.title, n.type, n.created_at FROM notes n "
            "LEFT JOIN relationships r ON r.source_path=n.path OR r.target_path=n.path "
            "LEFT JOIN dismissed_inbox_items d ON d.path=n.path AND d.item_type='note' "
            f"WHERE n.type IN ({type_placeholders}) "
            "AND (n.tags IS NULL OR n.tags='[]' OR n.tags='null' OR n.tags='') "
            "AND n.created_at >= datetime('now','-14 days') "
            "AND r.source_path IS NULL "
            "AND d.path IS NULL "
            "ORDER BY n.created_at DESC LIMIT 50",
            PROCESSABLE_TYPES,
        ).fetchall()
        unprocessed_notes = [dict(r) for r in unprocessed_rows]

        # --- Empty notes (body null or blank, not dismissed) ---
        empty_rows = conn.execute(
            "SELECT n.path, n.title FROM notes n "
            "LEFT JOIN dismissed_inbox_items d ON d.path=n.path AND d.item_type='note' "
            "WHERE (n.body IS NULL OR TRIM(n.body)='') "
            "AND d.path IS NULL "
            "LIMIT 20"
        ).fetchall()
        empty_notes = [dict(r) for r in empty_rows]

        total_count = len(unassigned_actions) + len(unprocessed_notes) + len(empty_notes)

        return jsonify({
            "unassigned_actions": unassigned_actions,
            "unassigned_actions_total": unassigned_actions_total,
            "unprocessed_notes": unprocessed_notes,
            "empty_notes": empty_notes,
            "total_count": total_count,
        })
    finally:
        conn.close()


@app.post("/inbox/dismiss")
def dismiss_inbox_item():
    """Persist a dismissed inbox item so it won't reappear."""
    data = request.get_json(force=True) or {}
    path = data.get("path", "")
    item_type = data.get("item_type", "")
    if not path or not item_type:
        return jsonify({"error": "path and item_type required"}), 400
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO dismissed_inbox_items (path, item_type) VALUES (?, ?)",
            (path, item_type),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"dismissed": True})


@app.post("/relationships")
def create_relationship():
    """Insert a link relationship between two notes."""
    data = request.get_json(force=True) or {}
    source = data.get("source_path", "")
    target = data.get("target_path", "")
    if not source or not target:
        return jsonify({"error": "source_path and target_path required"}), 400
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, 'link')",
            (source, target),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"created": True})


@app.post("/smart-capture")
def smart_capture():
    """Segment freeform text into typed notes and save atomically."""
    import itertools
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    from engine.segmenter import segment_blob
    from engine.capture import capture_note
    from engine.paths import BRAIN_ROOT
    import uuid

    source_url = data.get("source_url", "")
    source_type = data.get("source_type", "")
    segments = segment_blob(content)
    session_id = str(uuid.uuid4())
    conn = get_connection()

    saved = []
    try:
        for seg in segments:
            try:
                path = capture_note(
                    note_type=seg["type"], title=seg["title"], body=seg["body"],
                    tags=[], people=seg.get("entities", {}).get("people", []),
                    content_sensitivity="public", brain_root=BRAIN_ROOT, conn=conn,
                    url=source_url or None, source_type=source_type or None,
                )
                saved.append({"title": seg["title"], "type": seg["type"], "path": str(path)})
            except Exception as e:
                saved.append({"title": seg["title"], "type": seg["type"], "error": str(e)})

        # Co-captured relationships
        paths = [s["path"] for s in saved if "path" in s]
        now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        for a, b in itertools.combinations(paths, 2):
            conn.execute(
                "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
                (a, b, "co-captured"),
            )
        conn.commit()
    finally:
        conn.close()

    _broadcast({"type": "refresh"})
    return jsonify({"notes": saved, "capture_session": session_id, "count": len(saved)})


@app.get("/brain-health")
def brain_health_endpoint():
    """Brain content health dashboard: orphans, broken links, duplicates, score."""
    import sqlite3 as _sqlite3
    conn = get_connection()
    conn.row_factory = _sqlite3.Row
    try:
        from engine.brain_health import (
            get_orphan_notes,
            get_empty_notes,
            get_missing_file_notes,
            get_duplicate_candidates,
            get_stub_notes,
            compute_health_score,
            archive_old_action_items,
        )
        from engine.links import check_links
        from engine.paths import BRAIN_ROOT
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        orphans = get_orphan_notes(conn)
        empty = get_empty_notes(conn)
        stubs = get_stub_notes(conn)
        missing_files = get_missing_file_notes(conn)
        broken = check_links(BRAIN_ROOT, conn)
        duplicates = get_duplicate_candidates(conn)
        archived_count = archive_old_action_items(conn)
        score = compute_health_score(
            total_notes=total,
            orphans=len(orphans),
            broken=len(broken),
            duplicates=len(duplicates),
        )
        return jsonify(
            {
                "score": score,
                "total_notes": total,
                "orphan_count": len(orphans),
                "orphans": orphans[:20],
                "empty_count": len(empty),
                "empty_notes": empty[:20],
                "stub_count": len(stubs),
                "stub_notes": stubs[:20],
                "missing_file_count": len(missing_files),
                "missing_files": missing_files[:20],
                "broken_link_count": len(broken),
                "broken_links": broken[:20],
                "duplicate_count": len(duplicates),
                "duplicate_candidates": duplicates[:20],
                "archived_action_items": archived_count,
            }
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.post("/brain-health/merge")
def brain_health_merge():
    """Merge two duplicate notes. GUI-only endpoint — modal confirmation in frontend satisfies D-03.

    The MCP surface (sb_merge_confirm) uses the stricter confirm-token pattern.
    The CLI surface (sb-merge-duplicates) uses interactive prompts.
    This endpoint is called from the health panel merge button after user confirms in UI.

    Request JSON: {"keep_path": str, "discard_path": str}
    Response JSON: {"keep": str, "discarded": str, "merged_tags": list[str]}
    """
    data = request.get_json(force=True)
    keep = data.get("keep_path")
    discard = data.get("discard_path")
    if not keep or not discard:
        return jsonify({"error": "keep_path and discard_path required"}), 400
    conn = get_connection()
    try:
        from engine.brain_health import merge_notes
        result = merge_notes(keep, discard, conn)
        _broadcast({"type": "refresh"})
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


def startup() -> None:
    """Pre-serve initialization. Call before serve() in any startup path.

    Runs all DB migrations so existing databases pick up new tables
    (e.g. attachments) without requiring a manual schema reset.
    After migration, checks for empty-DB / notes-on-disk mismatch and
    populates _startup_warnings so /health can surface it.
    """
    import logging
    import glob as _glob
    from engine.db import init_schema

    logger = logging.getLogger(__name__)
    conn = get_connection()
    try:
        init_schema(conn)
        db_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    finally:
        conn.close()

    brain_root = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    disk_count = len(_glob.glob(f"{brain_root}/**/*.md", recursive=True))

    if db_count == 0 and disk_count > 0:
        msg = (
            f"DB is empty but {disk_count} note files exist on disk. "
            "Run `sb-reindex` to rebuild the index."
        )
        logger.warning("STARTUP HEALTH CHECK: %s", msg)
        _startup_warnings.append(msg)


def main():
    from waitress import serve
    startup()
    obs = start_note_observer()
    try:
        serve(app, host="127.0.0.1", port=37491, threads=8)
    finally:
        obs.stop()
        obs.join()


if __name__ == "__main__":
    main()
