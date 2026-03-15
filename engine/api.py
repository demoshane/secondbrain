"""Local HTTP sidecar for Second Brain GUI.

Exposes engine functions as HTTP endpoints on 127.0.0.1:37491.
The GUI must call this API only — never import engine modules directly.
"""
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine.db import get_connection
from engine.search import search_notes
from engine.intelligence import list_actions

app = Flask(__name__)
CORS(app, origins=["null", "file://*", "http://127.0.0.1:*"])


@app.get("/health")
def health():
    return jsonify({"status": "ok", "port": 37491})


@app.get("/notes")
def list_notes():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT path, title, type, created_at FROM notes ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify({"notes": [dict(r) for r in rows]})


@app.post("/search")
def search():
    body = request.get_json(force=True) or {}
    query = body.get("query", "")
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    results = search_notes(conn, query)
    conn.close()
    return jsonify({"results": results})


@app.get("/notes/<path:note_path>")
def read_note(note_path):
    p = Path(note_path) if note_path.startswith("/") else Path("/") / note_path
    if not p.exists():
        return jsonify({"error": "Not found"}), 404
    content = p.read_text(encoding="utf-8")
    return jsonify({"content": content, "path": str(p)})


@app.get("/actions")
def get_actions():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    actions = list_actions(conn, done=False)
    conn.close()
    return jsonify({"actions": actions})


def main():
    from waitress import serve
    serve(app, host="127.0.0.1", port=37491, threads=4)


if __name__ == "__main__":
    main()
