"""Scheduled consolidation job for brain hygiene.

Runs safe, idempotent cleanup operations. Does NOT auto-merge or auto-enrich.
Entry point: sb-consolidate (launchd daily at 03:00).
"""
import datetime
import json
import logging

logger = logging.getLogger(__name__)


def consolidate_main() -> None:
    """Entry point for sb-consolidate launchd job. Per D-16 order."""
    from engine.db import get_connection, init_schema
    from engine.brain_health import (
        archive_old_action_items,
        archive_old_audit_entries,
        delete_dangling_relationships,
        take_health_snapshot,
        cleanup_old_snapshots,
    )

    conn = get_connection()
    init_schema(conn)
    results = {}
    try:
        results["archived_actions"] = archive_old_action_items(conn)
        results["archived_audit"] = archive_old_audit_entries(conn)
        results["deleted_dangling"] = delete_dangling_relationships(conn)
        results["snapshot"] = take_health_snapshot(conn)
        results["cleaned_old_snapshots"] = cleanup_old_snapshots(conn)
    finally:
        conn.close()

    # Log to stdout — captured by launchd StandardOutPath
    print(json.dumps({"at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat(), **results}))
