"""Note deletion utility — single shared implementation for GUI and CLI."""
from __future__ import annotations

import datetime
from pathlib import Path


def delete_note(abs_path: Path, conn, brain_root: Path) -> dict:
    """Delete a single note: file + DB cascade + audit log.

    Raises NotImplementedError until Phase 22 Plan 02 implements this.
    """
    raise NotImplementedError("delete_note() not yet implemented — see 22-02-PLAN.md")
