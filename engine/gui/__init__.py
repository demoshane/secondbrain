"""Desktop GUI entry point for Second Brain.

Architecture constraint (C1): imports engine.api.app for the sidecar only.
All data operations go through HTTP — no direct engine module imports.
"""
import socket
import sys
import threading
import time
import urllib.request


API_PORT = 37491
API_URL = f"http://127.0.0.1:{API_PORT}"


def open_in_editor(path: str) -> None:
    """Exposed to JS via window.expose() — stateless, safe in any thread."""
    import os
    import subprocess
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


def _port_is_open(port: int) -> bool:
    """Return True if something is already listening on 127.0.0.1:<port>."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _start_sidecar(ready: threading.Event) -> None:
    """Start waitress in a daemon thread; set ready when /health responds."""
    from engine.api import app as flask_app, startup
    from waitress import serve

    startup()

    t = threading.Thread(
        target=serve,
        args=(flask_app,),
        kwargs={"host": "127.0.0.1", "port": API_PORT, "threads": 8},
        daemon=True,
    )
    t.start()
    for _ in range(100):   # up to 10 seconds
        try:
            urllib.request.urlopen(f"{API_URL}/health", timeout=0.1)
            ready.set()
            from engine.api import start_note_observer as _start_note_observer
            _start_note_observer()
            return
        except Exception:
            time.sleep(0.1)


def main() -> None:
    import webview

    ready = threading.Event()

    if _port_is_open(API_PORT):
        # sb-api already running — reuse it, no second sidecar needed
        ready.set()
    else:
        threading.Thread(target=_start_sidecar, args=(ready,), daemon=True).start()

    if not ready.wait(timeout=10):
        print("ERROR: API sidecar did not start within 10 seconds", file=sys.stderr)
        sys.exit(1)

    window = webview.create_window(
        "Second Brain",
        f"{API_URL}/ui",
        width=1280,
        height=800,
        min_size=(900, 600),
    )
    window.expose(open_in_editor)

    def on_closing():
        time.sleep(0.3)   # allow waitress to drain (Pitfall 5)

    window.events.closing += on_closing
    webview.start()
