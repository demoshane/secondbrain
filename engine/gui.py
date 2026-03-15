"""Desktop GUI entry point for Second Brain.

Starts Flask sidecar in a daemon thread, then opens a pywebview window
pointing at http://127.0.0.1:37491/ui.

Architecture constraint (C1): gui.py calls engine/api.py via HTTP only —
never imports engine modules directly (except api.app for the sidecar).
"""
import sys


def open_in_editor(path: str) -> None:
    """Exposed to JS via window.expose() — stateless OS shell open."""
    import subprocess
    import os
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.Popen(["xdg-open", path])


def main() -> None:
    raise NotImplementedError("GUI not yet implemented — Wave 2 plan")
