"""Local HTTP sidecar for Second Brain GUI.

Exposes engine functions as HTTP endpoints on 127.0.0.1:37491.
The GUI must call this API only — never import engine modules directly.
"""
import datetime
import json
import logging
import mimetypes
import os
import queue
import shutil
import sqlite3
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)
from pathlib import Path as _Path

import frontmatter as _fm
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from engine.db import PERSON_TYPES, PERSON_TYPES_PH, _escape_like, _json_list, _now_utc, get_connection, touch_note_access
import engine.paths as _engine_paths
from engine.paths import BRAIN_ROOT, store_path
from engine.links import traverse_graph
from engine.search import search_hybrid, search_notes, _apply_filters
from engine.intelligence import list_actions
from engine.watcher import suppress_next_delete


def _int_param(name: str, default: int, min_val: int | None = None, max_val: int | None = None) -> int:
    """Parse an integer query parameter, returning HTTP 400 on bad input."""
    raw = request.args.get(name, str(default))
    try:
        val = int(raw)
    except (ValueError, TypeError):
        from flask import abort
        abort(400, description=f"Invalid integer for '{name}': {raw}")
    if min_val is not None:
        val = max(val, min_val)
    if max_val is not None:
        val = min(val, max_val)
    return val


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

from engine.api_config import config_bp  # noqa: E402
app.register_blueprint(config_bp)


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
                logger.warning("SSE subscriber queue full — event dropped")


@app.get("/events")
def event_stream():
    from flask import Response, stream_with_context
    q = _subscribe()

    def generate():
        try:
            yield ": heartbeat\n\n"  # flush initial connection immediately (Waitress needs first chunk)
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
    brain_root = str(_engine_paths.BRAIN_ROOT)
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
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        if include_archived:
            total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            rows = conn.execute(
                "SELECT path, title, type, created_at, tags, importance FROM notes ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        else:
            total = conn.execute("SELECT COUNT(*) FROM notes WHERE archived = 0").fetchone()[0]
            rows = conn.execute(
                "SELECT path, title, type, created_at, tags, importance FROM notes WHERE archived = 0 ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    finally:
        conn.close()
    notes = []
    for r in rows:
        d = dict(r)
        d["tags"] = _json_list(d.get("tags"))
        d["folder"] = _note_folder(d["path"])
        d["importance"] = d.get("importance") or "medium"
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
    importance = body.get("importance")  # str | None
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
                # F-16: batch IN-clause instead of N+1 per-row queries
                candidate_paths = [r["path"] for r in rows]
                if candidate_paths:
                    placeholders = ",".join("?" * len(candidate_paths))
                    tag_rows = conn.execute(
                        f"SELECT note_path, tag FROM note_tags WHERE note_path IN ({placeholders})",  # noqa: S608
                        candidate_paths,
                    ).fetchall()
                    path_tags: dict[str, set[str]] = {}
                    for tr in tag_rows:
                        path_tags.setdefault(tr["note_path"], set()).add(tr["tag"])
                    rows = [r for r in rows if rest_tags.issubset(path_tags.get(r["path"], set()))]
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
            results = search_hybrid(query=query, conn=conn)
            if tags_filter:
                # F-16: batch IN-clause instead of N+1 per-row queries
                tags_set = set(tags_filter)
                candidate_paths = [r["path"] for r in results]
                if candidate_paths:
                    placeholders = ",".join("?" * len(candidate_paths))
                    tag_rows = conn.execute(
                        f"SELECT note_path, tag FROM note_tags WHERE note_path IN ({placeholders})",  # noqa: S608
                        candidate_paths,
                    ).fetchall()
                    path_tags: dict[str, set[str]] = {}
                    for tr in tag_rows:
                        path_tags.setdefault(tr["note_path"], set()).add(tr["tag"])
                    results = [r for r in results if tags_set.issubset(path_tags.get(r["path"], set()))]
        # Apply entity filters (person, tag, note_type, from_date, to_date) — AND logic
        results = _apply_filters(
            results, conn,
            person=person,
            tag=tag,
            note_type=note_type,
            from_date=from_date,
            to_date=to_date,
            importance=importance,
        )
    finally:
        conn.close()
    for r in results:
        if isinstance(r, dict):
            r["folder"] = _note_folder(r.get("path", ""))
    return jsonify({"results": results})


class _NP:
    """Resolved note path carrying absolute, relative, and brain_root forms."""
    __slots__ = ("absolute", "relative", "brain_root")

    def __init__(self, absolute: Path, relative: str, brain_root: Path):
        self.absolute = absolute
        self.relative = relative
        self.brain_root = brain_root

    # Backward compat: support `p, brain_root = _resolve_note_path(...)`
    def __iter__(self):
        return iter((self.absolute, self.brain_root))


def _resolve_note_path(note_path: str) -> _NP:
    """Resolve a Flask URL path to absolute, relative, and brain_root forms.

    Returns an _NP object with .absolute (Path), .relative (str), .brain_root (Path).
    Also supports tuple unpacking: ``p, brain_root = _resolve_note_path(...)``
    for backward compatibility.
    """
    brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))).resolve()
    if note_path.startswith("/"):
        p = Path(note_path).resolve()
    elif Path("/" + note_path).resolve().is_relative_to(brain_root):
        p = Path("/" + note_path).resolve()
    else:
        p = (brain_root / note_path).resolve()
    if not p.is_relative_to(brain_root):
        raise ValueError("path traversal")
    return _NP(absolute=p, relative=str(p.relative_to(brain_root)), brain_root=brain_root)


def _resolve_participant(conn, name: str) -> dict:
    """Best-effort resolve a participant name to a person note path. Path is null if no match."""
    row = conn.execute(
        "SELECT path FROM notes WHERE type IN ('person') AND title=?", (name,)
    ).fetchone()
    return {"name": name, "path": row["path"] if row else None}


@app.get("/notes/<path:note_path>")
def read_note(note_path):
    try:
        np = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not np.absolute.exists():
        return jsonify({"error": "Not found"}), 404
    try:
        raw = np.absolute.read_text(encoding="utf-8")
        if request.args.get("raw"):
            return jsonify({"content": raw, "path": np.relative})
        post = _fm.loads(raw)
        meta = post.metadata or {}
        tags = meta.get("tags", [])
        if isinstance(tags, str):
            import json as _json
            try:
                tags = _json.loads(tags)
            except Exception:
                tags = []
        people = meta.get("people", [])
        if isinstance(people, str):
            import json as _json
            try:
                people = _json.loads(people)
            except Exception:
                people = []
        rel_path = np.relative
        try:
            _conn = get_connection()
            touch_note_access(_conn, rel_path)
            _conn.close()
        except Exception:
            pass
        return jsonify({
            "body": post.content,
            "path": rel_path,
            "title": meta.get("title", np.absolute.stem),
            "type": meta.get("type", "note"),
            "tags": tags,
            "people": people,
            "folder": _note_folder(rel_path),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "importance": meta.get("importance", "medium"),
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/persons")
def list_people():
    from engine.people import list_people_with_metrics
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
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
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE type = 'meeting'"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT n.path, n.title, "
            "  COALESCE(n.meeting_date, substr(n.created_at,1,10)) AS meeting_date, n.people, "
            "  (SELECT COUNT(*) FROM action_items a WHERE a.note_path=n.path AND a.done=0) AS open_actions "
            "FROM notes n WHERE n.type = 'meeting' ORDER BY COALESCE(n.meeting_date, substr(n.created_at,1,10)) DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    result = []
    for r in rows:
        try:
            participants = _json_list(r["people"])
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
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, body, people, "
            "  COALESCE(meeting_date, substr(created_at,1,10)) AS meeting_date "
            "FROM notes WHERE path=?",
            (np.relative,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        try:
            raw_participants = _json_list(row["people"])
            participants = [_resolve_participant(conn, name) for name in raw_participants]
        except Exception:
            participants = []
        open_actions = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE note_path=? AND done=0",
            (np.relative,)
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
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE type IN ('project','projects')"
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT n.path, n.title, n.status, n.deadline, substr(n.updated_at,1,10) AS updated_at, "
            "  (SELECT COUNT(*) FROM action_items a WHERE a.note_path=n.path AND a.done=0) AS open_actions, "
            "  (SELECT COUNT(DISTINCT m.path) FROM notes m "
            "   JOIN relationships r ON (r.source_path=m.path OR r.target_path=m.path) "
            "   WHERE (r.source_path=n.path OR r.target_path=n.path) AND m.type='meeting') "
            "  AS linked_meetings_count "
            "FROM notes n WHERE n.type = 'projects' ORDER BY n.updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    finally:
        conn.close()
    return jsonify({"projects": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset})


@app.get("/projects/<path:note_path>")
def get_project(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        sp = np.relative
        row = conn.execute(
            "SELECT path, title, body, status, deadline, substr(updated_at,1,10) AS updated_at FROM notes WHERE path=?",
            (sp,)
        ).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        open_actions = conn.execute(
            "SELECT COUNT(*) FROM action_items WHERE note_path=? AND done=0",
            (sp,)
        ).fetchone()[0]
        related_notes_count = conn.execute(
            "SELECT COUNT(*) FROM relationships WHERE source_path=? OR target_path=?",
            (sp, sp)
        ).fetchone()[0]
        linked_meetings_count = conn.execute(
            "SELECT COUNT(DISTINCT n.path) FROM notes n "
            "JOIN relationships r ON (r.source_path=n.path OR r.target_path=n.path) "
            "WHERE (r.source_path=? OR r.target_path=?) AND n.type='meeting'",
            (sp, sp)
        ).fetchone()[0]
        linked_meetings_rows = conn.execute(
            "SELECT DISTINCT n.path, n.title, "
            "  COALESCE(n.meeting_date, substr(n.created_at,1,10)) AS meeting_date "
            "FROM notes n "
            "JOIN relationships r ON (r.source_path=n.path OR r.target_path=n.path) "
            "WHERE (r.source_path=? OR r.target_path=?) AND n.type='meeting' "
            "ORDER BY COALESCE(n.meeting_date, substr(n.created_at,1,10)) DESC",
            (sp, sp),
        ).fetchall()
        linked_meetings = [
            {"path": m["path"], "title": m["title"] or "", "meeting_date": m["meeting_date"] or ""}
            for m in linked_meetings_rows
        ]
    finally:
        conn.close()
    return jsonify({
        "path": row["path"],
        "title": row["title"] or "",
        "body": row["body"] or "",
        "status": row["status"] or "active",
        "deadline": row["deadline"] or None,
        "updated_at": row["updated_at"] or "",
        "open_actions": open_actions,
        "related_notes_count": related_notes_count,
        "linked_meetings_count": linked_meetings_count,
        "linked_meetings": linked_meetings,
    })


@app.put("/projects/<path:note_path>/status")
def update_project_status(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True) or {}
    status = data.get("status", "")
    if status not in VALID_PROJECT_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_PROJECT_STATUSES)}"}), 400
    conn = get_connection()
    try:
        sp = np.relative
        row = conn.execute("SELECT id FROM notes WHERE path=?", (sp,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE notes SET status=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE path=?",
            (status, sp),
        )
        conn.commit()
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"status": status, "path": sp})


@app.put("/notes/<path:note_path>/importance")
def update_note_importance(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True) or {}
    importance = data.get("importance", "")
    if importance not in VALID_IMPORTANCE_VALUES:
        return jsonify({"error": "importance must be low, medium, or high"}), 400
    conn = get_connection()
    try:
        sp = np.relative
        row = conn.execute("SELECT id FROM notes WHERE path=?", (sp,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        conn.execute(
            "UPDATE notes SET importance=?, updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE path=?",
            (importance, sp),
        )
        if abs_path.exists():
            post = _fm.load(str(abs_path))
            post["importance"] = importance
            from engine.capture import write_note_atomic
            write_note_atomic(abs_path, post, conn, update=True)
        else:
            conn.commit()
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"importance": importance, "path": sp})


@app.post("/projects/<path:note_path>/meetings")
def link_meeting_to_project(note_path):
    """Link a meeting note to a project via the relationships table."""
    data = request.get_json(force=True) or {}
    meeting_path = data.get("meeting_path", "").strip()
    if not meeting_path:
        return jsonify({"error": "meeting_path is required"}), 400

    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        sp = np.relative
        proj = conn.execute(
            "SELECT path, type FROM notes WHERE path=? AND type IN ('project','projects')", (sp,)
        ).fetchone()
        if not proj and sp != str(abs_path):
            # Fallback for pre-Phase-32 DBs that store absolute paths
            proj = conn.execute(
                "SELECT path, type FROM notes WHERE path=? AND type IN ('project','projects')", (str(abs_path),)
            ).fetchone()
            if proj:
                sp = str(abs_path)
        if not proj:
            proj_any = conn.execute(
                "SELECT path, type FROM notes WHERE path=?", (sp,)
            ).fetchone()
            if proj_any:
                return jsonify({
                    "error": f"Note found at '{sp}' but has wrong type '{proj_any['type']}' (expected 'project')"
                }), 404
            return jsonify({"error": f"Project not found: {sp}"}), 404

        try:
            np_mtg = _resolve_note_path(meeting_path)
            abs_mtg = np_mtg.absolute
            meeting_sp = np_mtg.relative
        except ValueError:
            return jsonify({"error": "Forbidden"}), 403

        # Try relative path first; fall back to raw meeting_path for pre-Phase-32 absolute-path DBs
        mtg = conn.execute(
            "SELECT path, type FROM notes WHERE path=? AND type='meeting'", (meeting_sp,)
        ).fetchone()
        if not mtg and meeting_sp != meeting_path:
            # Absolute path in DB — try the raw value as stored
            mtg = conn.execute(
                "SELECT path, type FROM notes WHERE path=? AND type='meeting'", (meeting_path,)
            ).fetchone()
            if mtg:
                meeting_sp = meeting_path
        if not mtg:
            mtg_any = conn.execute(
                "SELECT path, type FROM notes WHERE path=?", (meeting_sp,)
            ).fetchone()
            if mtg_any:
                return jsonify({
                    "error": f"Note found at '{meeting_sp}' but has wrong type '{mtg_any['type']}' (expected 'meeting')"
                }), 404
            return jsonify({"error": f"Meeting not found: {meeting_sp}"}), 404

        existing = conn.execute(
            "SELECT id FROM relationships WHERE "
            "(source_path=? AND target_path=?) OR (source_path=? AND target_path=?)",
            (sp, meeting_sp, meeting_sp, sp),
        ).fetchone()
        if not existing:
            try:
                conn.execute(
                    "INSERT INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
                    (sp, meeting_sp, "linked"),
                )
                conn.commit()
            except Exception as exc:
                return jsonify({"error": f"Failed to link: {type(exc).__name__}: {exc}"}), 500
    finally:
        conn.close()

    _broadcast({"type": "notes_changed", "path": sp})
    return jsonify({"project_path": sp, "meeting_path": meeting_sp, "linked": True})


@app.delete("/projects/<path:project_path>/meetings/<path:meeting_path>")
def unlink_meeting_from_project(project_path, meeting_path):
    """Remove a meeting↔project relationship."""
    try:
        np_proj = _resolve_note_path(project_path)
        abs_proj = np_proj.absolute
        np_mtg = _resolve_note_path(meeting_path)
        abs_mtg = np_mtg.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    sp = np_proj.relative
    mp = np_mtg.relative
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM relationships WHERE "
            "(source_path=? AND target_path=?) OR (source_path=? AND target_path=?)",
            (sp, mp, mp, sp),
        )
        conn.commit()
    finally:
        conn.close()
    _broadcast({"type": "notes_changed", "path": sp})
    return jsonify({"unlinked": True})


@app.delete("/relationships")
def delete_relationship():
    """Remove a specific relationship between two notes."""
    data = request.get_json(force=True) or {}
    source = data.get("source_path", "").strip()
    target = data.get("target_path", "").strip()
    if not source or not target:
        return jsonify({"error": "source_path and target_path required"}), 400
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM relationships WHERE "
            "(source_path=? AND target_path=?) OR (source_path=? AND target_path=?)",
            (source, target, target, source),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"deleted": True})


@app.post("/persons")
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
        brain_root = _engine_paths.BRAIN_ROOT

        # Check if person already exists (prevent duplicates from ensure_person_profile)
        existing = conn.execute(
            "SELECT path FROM notes WHERE type='person' AND LOWER(title)=LOWER(?)",
            (name,),
        ).fetchone()
        if existing:
            return jsonify({"error": "Person already exists", "path": existing[0]}), 409

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
    return jsonify({"path": store_path(result_path.resolve())}), 201


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
        brain_root = _engine_paths.BRAIN_ROOT
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
    return jsonify({"path": store_path(result_path.resolve())}), 201


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
        brain_root = _engine_paths.BRAIN_ROOT

        # Check if project already exists (prevent duplicates)
        existing = conn.execute(
            "SELECT path FROM notes WHERE type IN ('project','projects') AND LOWER(title)=LOWER(?)",
            (name,),
        ).fetchone()
        if existing:
            return jsonify({"error": "Project already exists", "path": existing[0]}), 409

        result_path = capture_note(
            note_type="project",
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
    return jsonify({"path": store_path(result_path.resolve())}), 201


@app.get("/persons/<path:note_path>/links")
def get_person_links(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    path_str = np.relative
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


@app.get("/persons/<path:note_path>/insight")
def get_person_insight(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        sp = np.relative
        row = conn.execute("SELECT type FROM notes WHERE path=?", (sp,)).fetchone()
        if row is None:
            return jsonify({"error": "Not found"}), 404
        if row["type"] not in ("person",):
            return jsonify({"error": "not a person note"}), 400
        force = request.args.get("force", "0") == "1"
        from engine.intelligence import generate_person_insight
        insight = generate_person_insight(conn, sp, force=force)
        return jsonify({"insight": insight, "person_path": sp})
    finally:
        conn.close()


@app.delete("/persons/<path:note_path>")
def delete_person(note_path):
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
        brain_root = np.brain_root
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    path_str = np.relative
    conn = get_connection()
    try:
        # Clear assignee references before delete (avoids orphan FK refs)
        conn.execute(
            "UPDATE action_items SET assignee_path = NULL WHERE assignee_path = ?",
            (path_str,)
        )
        # Remove from note_people junction — person column stores path or display name
        # Look up the person's title for name-format cleanup
        _title_row = conn.execute("SELECT title FROM notes WHERE path = ?", (path_str,)).fetchone()
        conn.execute("DELETE FROM note_people WHERE person = ?", (path_str,))
        if _title_row and _title_row[0]:
            conn.execute("DELETE FROM note_people WHERE LOWER(person) = LOWER(?)", (_title_row[0],))
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
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
        brain_root = np.brain_root
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
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
        brain_root = np.brain_root
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
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
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
            "tags": _json_list(r["tags"]),
            "description": r["description"] or "",
        })
    return jsonify({"links": result, "total": total_count})


@app.get("/links/<path:note_path>")
def get_link(note_path):
    from urllib.parse import urlparse
    try:
        np = _resolve_note_path(note_path)
        abs_path = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT path, title, url, body, substr(created_at,1,10) AS date, tags "
            "FROM notes WHERE path=? AND type='link'",
            (np.relative,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return jsonify({"error": "Not found"}), 404
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
        "tags": _json_list(row["tags"]),
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
    done_param = request.args.get("done")
    if done_param is None:
        done = None  # no filter — return all
    else:
        done = done_param == "1"
    assignee = request.args.get("assignee") or None
    note_path = request.args.get("note_path") or None
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        if done is None:
            total = conn.execute("SELECT COUNT(*) FROM action_items").fetchone()[0]
        else:
            total = conn.execute(
                "SELECT COUNT(*) FROM action_items WHERE done=?", (1 if done else 0,)
            ).fetchone()[0]
        actions = list_actions(conn, done=done, assignee=assignee, note_path=note_path)
    finally:
        conn.close()
    paginated = actions[offset:offset + limit]
    return jsonify({"actions": paginated, "total": total, "limit": limit, "offset": offset})


@app.get("/actions/grouped")
def get_actions_grouped():
    """Action items grouped by source note (per D-18)."""
    done = request.args.get("done", "0") == "1"
    assignee = request.args.get("assignee") or None
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        actions = list_actions(conn, done=done, assignee=assignee)

        note_paths = list({a["note_path"] for a in actions if a.get("note_path")})
        title_map = {}
        if note_paths:
            placeholders = ",".join("?" for _ in note_paths)
            title_rows = conn.execute(
                f"SELECT path, title FROM notes WHERE path IN ({placeholders})",
                note_paths,
            ).fetchall()
            title_map = {r["path"]: r["title"] or r["path"] for r in title_rows}
    finally:
        conn.close()

    from collections import defaultdict
    groups_map = defaultdict(list)
    for a in actions:
        np = a.get("note_path") or ""
        groups_map[np].append(a)

    groups = [
        {
            "note_path": np,
            "note_title": title_map.get(np, np),
            "actions": items,
        }
        for np, items in groups_map.items()
    ]
    groups.sort(key=lambda g: g["note_title"].lower())

    return jsonify({"groups": groups, "total": len(actions)})


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


def _atomic_save(p: Path, updated_text: str, db_fn) -> None:
    """DB-first atomic save: write temp, commit DB, then rename file.

    Args:
        p: Target note file path.
        updated_text: Full file content to write.
        db_fn: Callable(conn) that executes DB updates (without committing).

    Raises on DB or file failure; cleans up temp file on error.
    """
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
            f.write(updated_text)
            tmp = f.name
        conn = get_connection()
        try:
            db_fn(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        suppress_next_delete(str(p))
        os.replace(tmp, p)
        tmp = None  # rename succeeded; nothing to clean up
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


@app.put("/notes/<path:note_path>")
def save_note(note_path):
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
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
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET title=?, updated_at=? WHERE path=?",
            (title_val, now, np.relative)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # Body-only branch: when "body" present and "content"/"tags"/"title" absent
    body_val = body.get("body")
    if body_val is not None and "content" not in body and "tags" not in body and "title" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.content = body_val
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET body=?, updated_at=? WHERE path=?",
            (body_val, now, np.relative)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # Tags-only branch: when "tags" present and "content" absent, update frontmatter + DB only
    # Junction table (note_tags) auto-synced by SQLite trigger on UPDATE OF tags.
    tags_val = body.get("tags")
    if tags_val is not None and "content" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["tags"] = tags_val
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        path_str = np.relative
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET tags=?, updated_at=? WHERE path=?",
            (json.dumps(tags_val), now, path_str)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # People-only branch: junction table (note_people) auto-synced by SQLite trigger.
    people_val = body.get("people")
    if people_val is not None and "content" not in body and "tags" not in body and "title" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["people"] = people_val
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        path_str = np.relative
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET people=?, updated_at=? WHERE path=?",
            (json.dumps(people_val), now, path_str)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # Deadline branch: update deadline on project notes (or any note)
    if "deadline" in body and "content" not in body and "tags" not in body and "title" not in body and "people" not in body:
        deadline_val = body.get("deadline")  # None clears it, string sets it
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["deadline"] = deadline_val
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET deadline=?, updated_at=? WHERE path=?",
            (deadline_val, now, np.relative)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # Meeting date branch: update meeting_date on meeting notes
    if "meeting_date" in body and "content" not in body and "tags" not in body and "title" not in body and "people" not in body:
        meeting_date_val = body.get("meeting_date")
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["meeting_date"] = meeting_date_val
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET meeting_date=?, updated_at=? WHERE path=?",
            (meeting_date_val, now, np.relative)
        ))
        return jsonify({"saved": True, "path": str(p)})

    # Title+Body combined branch: update both title and body preserving all other frontmatter
    title_b = body.get("title_and_body_title")
    body_b = body.get("title_and_body_body")
    if title_b is not None and body_b is not None and "content" not in body:
        raw = p.read_text(encoding="utf-8")
        post = _fm.loads(raw)
        post.metadata["title"] = title_b
        post.content = body_b
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
        path_str = np.relative
        _atomic_save(p, _fm.dumps(post), lambda conn: conn.execute(
            "UPDATE notes SET title=?, body=?, updated_at=? WHERE path=?",
            (title_b, body_b, now, path_str)
        ))
        return jsonify({"saved": True, "path": str(p)})

    content = body.get("content", "")
    post = _fm.loads(content)
    title = post.metadata.get("title", p.stem)
    now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
    _atomic_save(p, content, lambda conn: conn.execute(
        "UPDATE notes SET title=?, updated_at=? WHERE path=?",
        (title, now, np.relative)
    ))
    return jsonify({"saved": True, "path": str(p)})


@app.post("/notes/<path:note_path>/rename")
def rename_note_route(note_path):
    from engine.rename import rename_note
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    body = request.get_json(force=True) or {}
    new_title = (body.get("title") or "").strip()
    if not new_title:
        return jsonify({"error": "title required"}), 400
    conn = get_connection()
    try:
        result = rename_note(p, new_title, _brain_root, conn)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()
    # Return relative new_path (consistent with how all note paths are stored/returned)
    result["new_path"] = store_path(result["new_path"])
    return jsonify({"saved": True, **result})


VALID_PROJECT_STATUSES = {"active", "paused", "completed"}
VALID_IMPORTANCE_VALUES = frozenset({"low", "medium", "high"})

VALID_NOTE_TYPES = {
    "note", "meeting", "person", "idea", "link",
    "project", "coding", "strategy", "personal", "files",
}


@app.post("/notes")
def create_note():
    data = request.get_json(force=True) or {}
    title = data.get("title", "untitled")
    note_type = data.get("type", "idea")
    note_body = data.get("body", "")
    source_url = data.get("source_url", "")
    if note_type not in VALID_NOTE_TYPES:
        return jsonify({"error": f"invalid note type: {note_type!r}"}), 400
    from engine.capture import capture_note
    from engine.db import init_schema
    conn = get_connection()
    try:
        init_schema(conn)
        brain_root = _engine_paths.BRAIN_ROOT
        result_path = capture_note(
            note_type=note_type,
            title=title,
            body=note_body,
            tags=[],
            people=[],
            content_sensitivity="public",
            brain_root=brain_root,
            conn=conn,
            url=source_url or None,
        )
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    rel_path = store_path(result_path.resolve())
    return jsonify({"path": rel_path}), 201


@app.delete("/notes/<path:note_path>")
def delete_note_endpoint(note_path):
    try:
        p, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not Found"}), 404
    from engine.delete import delete_note  # lazy import
    conn = get_connection()
    try:
        result = delete_note(p, conn, brain_root)
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify(result), 200


@app.get("/notes/<path:note_path>/impact")
def note_impact(note_path):
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    from engine.delete import get_delete_impact
    path_str = np.relative
    conn = get_connection()
    try:
        impact = get_delete_impact(path_str, conn)
        return jsonify(impact)
    finally:
        conn.close()


@app.get("/notes/<path:note_path>/meta")
def note_meta(note_path):
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    try:
        db_path = np.relative
        title_row = conn.execute(
            "SELECT title FROM notes WHERE path=?", (db_path,)
        ).fetchone()
        # F-05: use pre-computed relationships table instead of full-table body LIKE scan
        backlink_rows = conn.execute(
            "SELECT r.source_path AS path, n.title FROM relationships r "
            "JOIN notes n ON n.path = r.source_path "
            "WHERE r.target_path = ? AND r.rel_type = 'backlink'",
            (db_path,)
        ).fetchall()
        backlinks = [{"path": r["path"], "title": r["title"]} for r in backlink_rows]
        # Manual connections — bidirectional rel_type='connection'
        connection_rows = conn.execute(
            "SELECT CASE WHEN r.source_path=? THEN r.target_path ELSE r.source_path END AS path, "
            "n.title FROM relationships r "
            "JOIN notes n ON n.path = CASE WHEN r.source_path=? THEN r.target_path ELSE r.source_path END "
            "WHERE (r.source_path=? OR r.target_path=?) AND r.rel_type='connection'",
            (db_path, db_path, db_path, db_path)
        ).fetchall()
        connections = [{"path": r["path"], "title": r["title"]} for r in connection_rows]
        related = []
        if title_row:
            related_rows = search_notes(conn, title_row["title"])
            related = [r for r in related_rows if r.get("path") != db_path][:5]
        note_row = conn.execute(
            "SELECT people, body, tags FROM notes WHERE path=?", (db_path,)
        ).fetchone()
        raw_people = json.loads(note_row["people"]) if note_row and note_row["people"] else []
        note_body = note_row["body"] if note_row else ""
        note_tags = _json_list(note_row["tags"] if note_row else None)

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
                # Unresolved plain-text name — omit (noise from old entity extraction)
    finally:
        conn.close()
    return jsonify({"backlinks": backlinks, "connections": connections, "related": related, "people": people, "tags": note_tags})


@app.post("/notes/<path:note_path>/connections")
def add_note_connection(note_path):
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True) or {}
    target_path = data.get("target_path", "").strip()
    if not target_path:
        return jsonify({"error": "target_path required"}), 400
    conn = get_connection()
    try:
        source = np.relative
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
            (source, target_path, "connection"),
        )
        conn.commit()
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"status": "connected", "source": source, "target": target_path})


@app.delete("/notes/<path:note_path>/connections")
def remove_note_connection(note_path):
    try:
        np = _resolve_note_path(note_path)
        p = np.absolute
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    data = request.get_json(force=True) or {}
    target_path = data.get("target_path", "").strip()
    if not target_path:
        return jsonify({"error": "target_path required"}), 400
    conn = get_connection()
    try:
        source = np.relative
        conn.execute(
            "DELETE FROM relationships WHERE rel_type='connection' AND "
            "((source_path=? AND target_path=?) OR (source_path=? AND target_path=?))",
            (source, target_path, target_path, source),
        )
        conn.commit()
    finally:
        conn.close()
    _broadcast({"type": "notes_changed"})
    return jsonify({"status": "disconnected"})


@app.get("/files")
def list_files():
    limit = _int_param("limit", 50, min_val=1, max_val=200)
    offset = _int_param("offset", 0, min_val=0)
    files_dir = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))) / "files"
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


@app.get("/files/download")
def download_file():
    """Serve a file from the brain's files/ directory.

    Query param: path (absolute path, must be inside BRAIN_PATH/files/).
    """
    from flask import send_file as _send_file
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    files_dir = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))) / "files"
    target = _Path(file_path).resolve()

    try:
        target.relative_to(files_dir.resolve())
    except ValueError:
        return jsonify({"error": "Path outside files directory"}), 403

    if not target.exists():
        return jsonify({"error": "File not found"}), 404

    return _send_file(str(target), as_attachment=False)


@app.post("/files/open")
def open_file_native():
    """Open a file with the default macOS application (via `open`).

    Body: { "path": "/absolute/path/to/file" }
    Only paths inside BRAIN_PATH are permitted.
    """
    import subprocess
    body = request.get_json(force=True) or {}
    file_path = body.get("path", "")
    if not file_path:
        return jsonify({"error": "path required"}), 400

    target = _Path(file_path).resolve()
    brain_root = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))
    try:
        target.relative_to(brain_root.resolve())
    except ValueError:
        return jsonify({"error": "Path outside brain directory"}), 403

    if not target.exists():
        return jsonify({"error": "File not found"}), 404

    subprocess.Popen(["open", str(target)])
    return jsonify({"ok": True})


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

    files_dir = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))) / "files"
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
    # Use _engine_paths.BRAIN_ROOT (module attribute) so monkeypatched test values are picked up
    if not src_p.is_relative_to(_engine_paths.BRAIN_ROOT) or not dst_p.is_relative_to(_engine_paths.BRAIN_ROOT):
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

    _br = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))
    dest = _br / "files" / filename

    # Collision handling: append counter suffix before extension
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        counter = 2
        while dest.exists():
            dest = _br / "files" / f"{stem}-{counter}{suffix}"
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
    already present in the notes table, inserts absent ones with full metadata
    (tags, people, sensitivity). Junction tables auto-sync via SQLite triggers.
    """
    import frontmatter as _fm_batch

    brain_root = _Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain")))

    conn = get_connection()
    try:
        existing = {
            row[0] for row in conn.execute("SELECT path FROM notes").fetchall()
        }

        succeeded = []
        failed = []

        for md_file in brain_root.rglob("*.md"):
            if any(part.startswith(".") for part in md_file.relative_to(brain_root).parts):
                continue

            rel_path = str(md_file.relative_to(brain_root))
            if rel_path in existing:
                continue

            try:
                text = md_file.read_text(encoding="utf-8", errors="ignore")
                post = _fm_batch.loads(text)
                meta = post.metadata or {}
                title = meta.get("title", md_file.stem)
                note_type = meta.get("type", "note")
                body = post.content or ""
                tags = meta.get("tags", [])
                if not isinstance(tags, list):
                    tags = [str(tags)]
                people = meta.get("people", [])
                if not isinstance(people, list):
                    people = [str(people)]
                now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
                conn.execute(
                    "INSERT INTO notes (path, title, type, body, tags, people, "
                    "created_at, updated_at, sensitivity, url) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (rel_path, title, note_type, body,
                     json.dumps(tags), json.dumps(people),
                     meta.get("created_at", now), now,
                     meta.get("content_sensitivity", "public"),
                     meta.get("url") or None),
                )
                succeeded.append({"path": rel_path, "title": title})
            except Exception as exc:
                failed.append({"path": rel_path, "error": str(exc)})

        # Also register any files in files/ not yet tracked in attachments table
        files_dir = brain_root / "files"
        if files_dir.exists():
            tracked_files = {
                row[0] for row in conn.execute("SELECT file_path FROM attachments").fetchall()
            }
            now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat()
            for f in sorted(files_dir.rglob("*")):
                if not f.is_file():
                    continue
                rel_file = str(f.relative_to(brain_root))
                if rel_file in tracked_files:
                    continue
                try:
                    conn.execute(
                        "INSERT INTO attachments (note_path, file_path, filename, size, uploaded_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        ("", rel_file, f.name, f.stat().st_size, now),
                    )
                    succeeded.append({"path": rel_file, "title": f.name})
                except Exception as exc:
                    failed.append({"path": rel_file, "error": str(exc)})

        conn.commit()
    finally:
        conn.close()

    _broadcast({"type": "created", "path": ""})
    return jsonify({"succeeded": succeeded, "failed": failed}), 200


@app.post("/actions")
def create_action():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    note_path = data.get("note_path") or None
    assignee_path = data.get("assignee_path") or None
    due_date = data.get("due_date") or None
    description = data.get("description") or None
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO action_items (note_path, text, assignee_path, due_date, description) VALUES (?, ?, ?, ?, ?)",
            (note_path, text, assignee_path, due_date, description),
        )
        conn.commit()
        action_id = cur.lastrowid
    finally:
        conn.close()
    return jsonify({"id": action_id, "text": text, "note_path": note_path, "assignee_path": assignee_path, "due_date": due_date, "description": description, "done": False}), 201


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
        if "note_path" in data:
            conn.execute(
                "UPDATE action_items SET note_path=? WHERE id=?",
                (data["note_path"] or None, action_id),
            )
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
        if "description" in data:
            conn.execute(
                "UPDATE action_items SET description=? WHERE id=?",
                (data["description"] or None, action_id),
            )
        if "text" in data:
            new_text = (data["text"] or "").strip()
            if new_text:
                conn.execute(
                    "UPDATE action_items SET text=? WHERE id=?",
                    (new_text, action_id),
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


@app.get("/intelligence/synthesis")
def intelligence_synthesis():
    """On-demand weekly synthesis. Regenerated on every call (per D-09)."""
    conn = get_connection()
    try:
        from engine.intelligence import generate_weekly_synthesis
        text = generate_weekly_synthesis(conn)
        return jsonify({"synthesis": text})
    except Exception as exc:
        return jsonify({"synthesis": f"Error: {exc}"}), 500
    finally:
        conn.close()


@app.post("/ask")
def ask_brain_endpoint():
    """Answer a freeform question using the brain's notes as context.

    Request JSON: {question: str, history?: [{question: str, answer: str}, ...]}
    """
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    history = data.get("history") or []
    conn = get_connection()
    try:
        from engine.intelligence import ask_brain
        result = ask_brain(question, conn, history=history)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        conn.close()


@app.get("/inbox")
def get_inbox():
    """Return inbox items: unassigned actions, unprocessed notes, empty notes."""
    PAGE_SIZE = 20
    actions_offset = _int_param("actions_offset", 0, min_val=0)
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
                "SELECT a.id, a.note_path, a.text, a.created_at, a.due_date, a.description, a.assignee_path FROM action_items a "
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
                "SELECT a.id, a.note_path, a.text, a.created_at, a.due_date, a.description, a.assignee_path FROM action_items a "
                "LEFT JOIN dismissed_inbox_items d ON d.path=CAST(a.id AS TEXT) AND d.item_type='action' "
                "WHERE a.done=0 AND a.assignee_path IS NULL AND d.path IS NULL "
                "ORDER BY a.created_at DESC LIMIT ? OFFSET ?",
                (PAGE_SIZE, actions_offset),
            ).fetchall()
        unassigned_actions_total = total_row[0] if total_row else 0
        unassigned_actions = [dict(r) for r in action_rows]

        # --- Unprocessed notes (14-day window, no tags, no relationships, structured types only) ---
        PROCESSABLE_TYPES = ('idea', 'ideas', 'coding', 'strategy', 'personal', 'project', 'projects')
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
    """Insert a relationship between two notes. rel_type defaults to 'connection'."""
    data = request.get_json(force=True) or {}
    source = data.get("source_path", "")
    target = data.get("target_path", "")
    rel_type = data.get("rel_type", "connection")
    if not source or not target:
        return jsonify({"error": "source_path and target_path required"}), 400
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?, ?, ?)",
            (source, target, rel_type),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"created": True})


@app.get("/graph/overview")
def graph_overview():
    """Return all relationships as nodes + edges for full graph view."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT source_path FROM relationships "
            "UNION SELECT DISTINCT target_path FROM relationships"
        ).fetchall()
        note_paths = [r[0] for r in rows]

        nodes = []
        for p in note_paths:
            row = conn.execute(
                "SELECT title, type FROM notes WHERE path = ?", (p,)
            ).fetchone()
            title = row[0] if row else p.rsplit("/", 1)[-1].replace(".md", "")
            note_type = row[1] if row else "unknown"
            nodes.append({"path": p, "title": title, "note_type": note_type})

        edges_rows = conn.execute(
            "SELECT source_path, target_path, rel_type, "
            "COALESCE(strength, 1.0) as strength FROM relationships"
        ).fetchall()
        edges = [
            {"source": r[0], "target": r[1], "type": r[2], "strength": r[3]}
            for r in edges_rows
        ]
    finally:
        conn.close()
    return jsonify({"nodes": nodes, "edges": edges})


@app.get("/graph")
def graph_traverse():
    """Return traversal subgraph from a starting note."""
    start = request.args.get("start", "")
    if not start:
        return jsonify({"error": "start parameter required"}), 400
    depth = min(int(request.args.get("depth", "2")), 3)
    types_param = request.args.get("types", "")
    rel_types = [t.strip() for t in types_param.split(",") if t.strip()] or None
    conn = get_connection()
    try:
        result = traverse_graph(conn, start, max_depth=depth, rel_types=rel_types)
    finally:
        conn.close()
    return jsonify(result)


@app.post("/smart-capture")
def smart_capture():
    """Segment freeform text into typed notes and save atomically.

    High-confidence segments (>= CONFIDENCE_THRESHOLD) are saved immediately.
    Low-confidence segments are returned as 'pending_review' for the caller to
    confirm the type before saving via POST /smart-capture/confirm.

    Uses the multi-pass decompose() pipeline (Pass 1-5) instead of the legacy
    segment_blob(). Produces person stubs, link notes, and keyword action items
    at capture time (GUI/MCP parity).
    """
    import itertools
    data = request.get_json() or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    from engine.passes import decompose, CONFIDENCE_THRESHOLD
    from engine.capture import capture_note
    import uuid

    source_url = data.get("source_url", "")
    source_type = data.get("source_type", "")
    session_id = str(uuid.uuid4())
    conn = get_connection()
    results = decompose(content, conn=conn, brain_root=_engine_paths.BRAIN_ROOT)

    saved = []
    pending_review = []
    person_stubs_created: list[str] = []

    try:
        for result in results:
            confidence = result.confidence
            if confidence < CONFIDENCE_THRESHOLD:
                # Return to caller for type confirmation
                pending_review.append({
                    "title": result.primary_title,
                    "body": result.primary_body,
                    "suggested_type": result.primary_type,
                    "confidence": round(confidence, 2),
                    "people": result.entities.get("people", []),
                })
                continue

            # (a) Link notes first (per D-04)
            for link in result.link_notes:
                try:
                    link_path = capture_note(
                        note_type="link",
                        title=link.title,
                        body=link.body,
                        tags=[],
                        people=[],
                        content_sensitivity="public",
                        brain_root=_engine_paths.BRAIN_ROOT,
                        conn=conn,
                        url=link.url,
                        source_type=source_type or None,
                    )
                    saved.append({
                        "title": link.title,
                        "type": "link",
                        "confidence": 1.0,
                        "path": str(link_path),
                    })
                except Exception:
                    pass  # Non-fatal

            # (b) Person stubs (per D-12 — GUI/MCP parity)
            for stub in result.person_stubs:
                stub_name = stub["name"]
                if stub_name in person_stubs_created:
                    continue
                try:
                    stub_path = capture_note(
                        note_type=stub["type"],
                        title=stub_name,
                        body="",
                        tags=[],
                        people=[],
                        content_sensitivity="public",
                        brain_root=_engine_paths.BRAIN_ROOT,
                        conn=conn,
                    )
                    person_stubs_created.append(stub_name)
                    saved.append({
                        "title": stub_name,
                        "type": stub["type"],
                        "confidence": 1.0,
                        "path": str(stub_path),
                        "is_stub": True,
                    })
                except Exception:
                    pass  # Non-fatal

            # (c) Primary note
            try:
                path = capture_note(
                    note_type=result.primary_type,
                    title=result.primary_title,
                    body=result.primary_body,
                    tags=[],
                    people=result.entities.get("people", []),
                    content_sensitivity="public",
                    brain_root=_engine_paths.BRAIN_ROOT,
                    conn=conn,
                    url=source_url or None,
                    source_type=source_type or None,
                )
                saved.append({
                    "title": result.primary_title,
                    "type": result.primary_type,
                    "confidence": round(confidence, 2),
                    "path": str(path),
                })

                # (d) Keyword action items from Pass 4 (per D-08)
                for ai in result.action_items:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO action_items"
                            " (note_path, text, created_at)"
                            " VALUES (?, ?, datetime('now'))",
                            (str(path), ai.text),
                        )
                    except Exception:
                        pass  # Non-fatal

            except Exception as e:
                saved.append({
                    "title": result.primary_title,
                    "type": result.primary_type,
                    "error": str(e),
                })

        # Co-captured relationships between all saved notes
        all_paths = [s["path"] for s in saved if "path" in s]
        for a, b in itertools.combinations(all_paths, 2):
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO relationships (source_path, target_path, rel_type) VALUES (?,?,?)",
                    (a, b, "co-captured"),
                )
            except Exception:
                pass  # Non-fatal — FK constraint may fail if path format mismatches
        conn.commit()
    finally:
        conn.close()

    _broadcast({"type": "refresh"})
    return jsonify({
        "notes": saved,
        "capture_session": session_id,
        "count": len(saved),
        "pending_review": pending_review,
        "person_stubs": person_stubs_created,
    })


@app.post("/smart-capture/confirm")
def smart_capture_confirm():
    """Save pending smart-capture segments after user has confirmed their types.

    Expects JSON body:
      {
        "segments": [
          {"title": str, "type": str, "body": str, "people": [str]},
          ...
        ],
        "capture_session": str  (optional, for co-captured relationship linking)
      }
    """
    import itertools
    data = request.get_json() or {}
    segments = data.get("segments", [])
    if not segments:
        return jsonify({"error": "segments is required"}), 400

    from engine.capture import capture_note
    import uuid

    session_id = data.get("capture_session") or str(uuid.uuid4())
    conn = get_connection()
    saved = []
    try:
        for seg in segments:
            note_type = seg.get("type", "note")
            title = seg.get("title", "Untitled")
            body = seg.get("body", "")
            people = seg.get("people", [])
            if note_type not in VALID_NOTE_TYPES:
                saved.append({"title": title, "type": note_type, "error": f"invalid type: {note_type!r}"})
                continue
            try:
                path = capture_note(
                    note_type=note_type, title=title, body=body,
                    tags=[], people=people,
                    content_sensitivity="public", brain_root=_engine_paths.BRAIN_ROOT, conn=conn,
                )
                saved.append({"title": title, "type": note_type, "path": str(path)})
            except Exception as e:
                saved.append({"title": title, "type": note_type, "error": str(e)})

        paths = [s["path"] for s in saved if "path" in s]
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
        total = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        orphans = get_orphan_notes(conn)
        empty = get_empty_notes(conn)
        stubs = get_stub_notes(conn)
        missing_files = get_missing_file_notes(conn)
        broken = check_links(_engine_paths.BRAIN_ROOT, conn)
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


@app.post("/brain-health/dismiss-duplicate")
def dismiss_duplicate():
    """Mark a duplicate pair as 'not duplicate' so it won't reappear in health checks.

    Stores the similarity score at dismissal time. If the pair's similarity later
    shifts by >5%, the pair resurfaces automatically.
    """
    data = request.get_json(force=True) or {}
    a = (data.get("a") or "").strip()
    b = (data.get("b") or "").strip()
    similarity = data.get("similarity", 0)
    if not a or not b:
        return jsonify({"error": "a and b paths required"}), 400
    key = "||".join(sorted([a, b]))
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO dismissed_inbox_items (path, item_type, detail) VALUES (?, 'duplicate', ?)",
            (key, str(similarity)),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"dismissed": True, "pair": [a, b]})


@app.post("/summarise-url")
def summarise_url():
    """Summarise a web page's content via LLM.

    Request JSON: {url: str, content: str (page text, truncated to 8000 chars server-side)}
    Response JSON: {summary: str}
    """
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    content = (data.get("content") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    if not content:
        return jsonify({"error": "content is required"}), 400

    # Truncate server-side regardless of what client sends
    content = content[:8000]

    try:
        from engine.intelligence import _router
        from engine.paths import CONFIG_PATH
        adapter = _router.get_adapter("public", CONFIG_PATH)
        system_prompt = (
            "You are a concise summariser. Given the text of a web page, write a clear "
            "1-3 paragraph summary capturing the key points, main arguments, and any "
            "important conclusions. Be factual and objective."
        )
        summary = adapter.generate(
            user_content=f"URL: {url}\n\n{content}",
            system_prompt=system_prompt,
        )
        return jsonify({"summary": summary})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.get("/perf/results")
def perf_list_results():
    from engine.perf import list_result_dates
    return jsonify({"dates": list_result_dates()})


@app.get("/perf/results/latest")
def perf_latest():
    from engine.perf import get_latest_with_previous
    data = get_latest_with_previous()
    return jsonify(data)


@app.get("/perf/results/<date>")
def perf_by_date(date: str):
    from flask import abort
    from engine.perf import get_result_by_date
    result = get_result_by_date(date)
    if result is None:
        abort(404)
    return jsonify(result)


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

    brain_root = str(_engine_paths.BRAIN_ROOT)
    disk_count = len(_glob.glob(f"{brain_root}/**/*.md", recursive=True))

    if db_count == 0 and disk_count > 0:
        msg = (
            f"DB is empty but {disk_count} note files exist on disk. "
            "Run `sb-reindex` to rebuild the index."
        )
        logger.warning("STARTUP HEALTH CHECK: %s", msg)
        _startup_warnings.append(msg)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=37491)
    parser.add_argument("--dev", action="store_true",
                        help="Use Flask dev server (no thread pool limit, better for tests)")
    args = parser.parse_args()

    startup()
    obs = start_note_observer()
    try:
        if args.dev:
            # Flask dev server: one thread per request, no pool exhaustion from SSE
            app.run(host="127.0.0.1", port=args.port, use_reloader=False, threaded=True)
        else:
            from waitress import serve
            serve(app, host="127.0.0.1", port=args.port, threads=8)
    finally:
        obs.stop()
        obs.join()


if __name__ == "__main__":
    main()
