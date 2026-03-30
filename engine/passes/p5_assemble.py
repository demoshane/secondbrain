"""Pass 5: entity resolution — populates person_stubs and existing_people on DecomposedResult.

Does NOT write to DB. Produces the blueprint; callers handle persistence.
"""
import sqlite3
from pathlib import Path

from engine.passes import DecomposedResult


def assemble(
    segments: list[DecomposedResult],
    conn: sqlite3.Connection,
    brain_root: Path,
) -> list[DecomposedResult]:
    """Resolve entities in each segment to existing notes or new stubs.

    For each segment with entities, calls resolve_entities() to classify
    each person as either an existing note (existing_people) or a new
    entity to be created (person_stubs).

    Mutates and returns the input list — no DB writes occur here.
    """
    from engine.segmenter import resolve_entities

    for result in segments:
        if not result.entities:
            continue
        resolution = resolve_entities(result.entities, conn, brain_root)
        result.person_stubs = resolution.get("new_stubs", [])
        result.existing_people = resolution.get("existing", [])

    return segments
