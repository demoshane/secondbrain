"""Local HTTP sidecar for Second Brain GUI.

Exposes engine functions as HTTP endpoints on 127.0.0.1:37491.
The GUI must call this API only — never import engine modules directly.
"""
import datetime
import json
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

from engine.db import get_connection
from engine.search import search_notes
from engine.intelligence import list_actions
from engine.watcher import suppress_next_delete

_STATIC_DIR = _Path(__file__).parent / "gui" / "static"

class _SlashNormMiddleware:
    """Collapse double-slash after known prefixes so /notes//abs/path → /notes/abs/path.

    When tests pass absolute paths like /notes//private/var/... the double
    slash prevents Flask route matching. This middleware rewrites PATH_INFO
    before routing so the path converter receives the absolute path correctly.
    """

    def __init__(self, wsgi_app):
        self._app = wsgi_app

    def __call__(self, environ, start_response):
        import re
        path = environ.get("PATH_INFO", "")
        # Rewrite /notes//abs → /notes/abs and /notes//abs/x/meta → /notes/abs/x/meta
        new_path = re.sub(r"^/(notes|files)//", r"/\1/", path)
        environ["PATH_INFO"] = new_path
        return self._app(environ, start_response)


app = Flask(__name__)
app.wsgi_app = _SlashNormMiddleware(app.wsgi_app)
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*"])


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
    return jsonify({"status": "ok", "port": 37491})


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
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT path, title, type, created_at, tags FROM notes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    notes = []
    for r in rows:
        d = dict(r)
        d["tags"] = json.loads(d.get("tags") or "[]")
        notes.append(d)
    return jsonify({"notes": notes})


@app.post("/search")
def search():
    body = request.get_json(force=True) or {}
    query = body.get("query", "")
    tags_filter = body.get("tags")  # list[str] | None
    conn = get_connection()
    conn.row_factory = sqlite3.Row

    if tags_filter and not query:
        # Tags-only filter: fetch all notes and filter by tags in Python
        rows = conn.execute(
            "SELECT path, type, title, created_at, tags FROM notes ORDER BY created_at DESC"
        ).fetchall()
        results = []
        for r in rows:
            note_tags = json.loads(r["tags"] or "[]")
            if all(t in note_tags for t in tags_filter):
                results.append({
                    "path": r["path"],
                    "type": r["type"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "score": 0.0,
                })
    else:
        results = search_notes(conn, query)
        if tags_filter:
            filtered = []
            for r in results:
                row = conn.execute(
                    "SELECT tags FROM notes WHERE path=?", (r["path"],)
                ).fetchone()
                if row:
                    note_tags = json.loads(row["tags"] or "[]")
                    if all(t in note_tags for t in tags_filter):
                        filtered.append(r)
            results = filtered

    conn.close()
    return jsonify({"results": results})


def _resolve_note_path(note_path: str) -> tuple[Path, Path]:
    """Return (abs_path, brain_root). Raises ValueError if path escapes brain_root."""
    brain_root = Path(os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))).resolve()
    p = (Path(note_path) if note_path.startswith("/") else (Path("/") / note_path)).resolve()
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
    return jsonify({"body": post.content, "path": str(p)})


@app.get("/actions")
def get_actions():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    actions = list_actions(conn, done=False)
    conn.close()
    return jsonify({"actions": actions})


@app.get("/ui")
def gui_shell():
    return (_STATIC_DIR / "index.html").read_text(encoding="utf-8")


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
        conn.execute(
            "UPDATE notes SET tags=?, updated_at=? WHERE path=?",
            (json.dumps(tags_val), now, str(p.resolve()))
        )
        conn.commit()
        conn.close()
        return jsonify({"saved": True, "path": str(p)})

    content = body.get("content", "")
    with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False, suffix=".tmp", encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    os.replace(tmp, p)
    suppress_next_delete(str(p))
    saved_text = p.read_text(encoding="utf-8")
    post = _fm.loads(saved_text)
    title = post.metadata.get("title", p.stem)
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    conn.execute(
        "UPDATE notes SET title=?, updated_at=? WHERE path=?",
        (title, now, str(p.resolve()))
    )
    conn.commit()
    conn.close()
    return jsonify({"saved": True, "path": str(p)})


@app.post("/notes")
def create_note():
    body = request.get_json(force=True) or {}
    title = body.get("title", "untitled")
    note_type = body.get("type", "idea")
    note_body = body.get("body", "")
    brain_path = body.get("brain_path", "")
    if not brain_path:
        return jsonify({"error": "brain_path required"}), 400
    import datetime
    slug = datetime.date.today().isoformat() + "-" + title[:40].replace(" ", "-").lower()
    subdir = "ideas" if note_type == "idea" else note_type
    target = _Path(brain_path) / subdir / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    today = datetime.date.today().isoformat()
    md_content = (
        f"---\ntype: {note_type}\ntitle: {title}\ndate: {today}\n"
        f"tags: []\npeople: []\ncreated_at: {now}\nupdated_at: {now}\n"
        f"content_sensitivity: public\n---\n\n{note_body}\n"
    )
    target.write_text(md_content, encoding="utf-8")
    return jsonify({"path": str(target)}), 201


@app.delete("/notes/<path:note_path>")
def delete_note_endpoint(note_path):
    try:
        p, brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    try:
        from engine.delete import delete_note  # lazy import
        conn = get_connection()
        result = delete_note(p, conn, brain_root)
        conn.close()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": type(e).__name__}), 500


@app.get("/notes/<path:note_path>/meta")
def note_meta(note_path):
    try:
        p, _brain_root = _resolve_note_path(note_path)
    except ValueError:
        return jsonify({"error": "Forbidden"}), 403
    p = _Path(note_path) if note_path.startswith("/") else _Path("/") / note_path
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    title_row = conn.execute(
        "SELECT title FROM notes WHERE path=?", (str(p),)
    ).fetchone()
    if title_row and title_row["title"]:
        rows = conn.execute(
            "SELECT path, title FROM notes "
            "WHERE path != ? AND LOWER(body) LIKE LOWER(?)",
            (str(p), f"%{title_row['title']}%"),
        ).fetchall()
        backlinks = [dict(r) for r in rows]
    else:
        backlinks = []
    related = []
    if title_row:
        related_rows = search_notes(conn, title_row["title"])
        related = [r for r in related_rows if r.get("path") != str(p)][:5]
    conn.close()
    return jsonify({"backlinks": backlinks, "related": related})


@app.get("/files")
def list_files():
    brain_path = os.environ.get("BRAIN_PATH", os.path.expanduser("~/SecondBrain"))
    files_dir = _Path(brain_path) / "files"
    file_list = []
    if files_dir.exists():
        for f in sorted(files_dir.rglob("*")):
            if f.is_file():
                file_list.append({
                    "path": str(f),
                    "name": f.name,
                    "rel_path": str(f.relative_to(files_dir)),
                    "size": f.stat().st_size,
                })
    return jsonify({"files": file_list})


@app.post("/files/move")
def move_file():
    body = request.get_json(force=True) or {}
    src = body.get("src", "")
    dst = body.get("dst", "")
    if not src or not dst:
        return jsonify({"error": "src and dst required"}), 400
    src_p = _Path(src)
    dst_p = _Path(dst)
    if not src_p.exists():
        return jsonify({"error": "src not found"}), 404
    dst_p.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src_p), str(dst_p))
    return jsonify({"moved": True, "dst": str(dst_p)})


@app.post("/actions/<int:action_id>/done")
def action_done(action_id):
    conn = get_connection()
    conn.execute("UPDATE action_items SET done=1 WHERE id=?", (action_id,))
    conn.commit()
    conn.close()
    return jsonify({"done": True, "id": action_id})


@app.get("/intelligence")
def get_intelligence():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    from engine.intelligence import get_stale_notes
    try:
        nudge_rows = get_stale_notes(conn, limit=5)
        nudges = nudge_rows if isinstance(nudge_rows, list) else []
    except Exception:
        nudges = []
    conn.close()
    return jsonify({"recap": None, "nudges": nudges})


def main():
    from waitress import serve
    obs = start_note_observer()
    try:
        serve(app, host="127.0.0.1", port=37491, threads=8)
    finally:
        obs.stop()
        obs.join()


if __name__ == "__main__":
    main()
