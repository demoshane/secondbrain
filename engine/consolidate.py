"""Scheduled consolidation job for brain hygiene and synthesis.

Runs safe, idempotent cleanup operations, then generates synthesis notes
from clusters of related recent notes. Entry point: sb-consolidate
(launchd daily at 03:00).
"""
import datetime
import json
import logging

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = (
    "You are a knowledge synthesizer. Given a cluster of related notes about a topic, "
    "write a concise synthesis. Include:\n"
    "1. **Summary** — what happened across these notes\n"
    "2. **Key Decisions** — decisions made or positions taken\n"
    "3. **Open Questions** — unresolved items or contradictions\n"
    "4. **Action Items** — aggregated from the notes\n\n"
    "Be concise. Use bullet points. Do not repeat verbatim — synthesize."
)


def synthesize_clusters(conn) -> dict:
    """Generate synthesis notes for qualifying clusters of recent notes.

    Returns: {"clusters_found": N, "syntheses_created": N, "skipped_existing": N}
    """
    from engine.intelligence import cluster_recent_notes
    from engine.paths import BRAIN_ROOT, CONFIG_PATH

    clusters = cluster_recent_notes(conn)
    stats = {"clusters_found": len(clusters), "syntheses_created": 0, "skipped_existing": 0}

    if not clusters:
        return stats

    # Check for existing recent syntheses to dedup
    cutoff = (
        datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        - datetime.timedelta(days=7)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    for cluster in clusters:
        notes = cluster["notes"]
        topic = cluster["topic"]

        # Dedup: check if synthesis already exists for overlapping source_notes
        existing = conn.execute(
            "SELECT path, body FROM notes WHERE type = 'synthesis' AND created_at >= ?",
            (cutoff,),
        ).fetchall()

        skip = False
        for (ex_path, ex_body) in existing:
            # Check if existing synthesis covers >50% of this cluster
            covered = sum(1 for n in notes if n in (ex_body or ""))
            if covered > len(notes) * 0.5:
                skip = True
                break

        if skip:
            stats["skipped_existing"] += 1
            continue

        # Read source note bodies
        note_texts = []
        for path in notes:
            row = conn.execute("SELECT title, body FROM notes WHERE path = ?", (path,)).fetchone()
            if row:
                note_texts.append(f"### {row[0]}\n{row[1][:2000]}")

        if not note_texts:
            continue

        combined = f"Topic: {topic}\n\n" + "\n\n---\n\n".join(note_texts)

        # Generate synthesis via AI adapter
        try:
            from engine.intelligence import _router
            adapter = _router.get_adapter("public", CONFIG_PATH)
            synthesis_body = adapter.generate(
                user_content=combined[:8000],
                system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            )
        except Exception as exc:
            logger.warning("Synthesis generation failed for cluster %s: %s", topic, exc)
            synthesis_body = f"*Synthesis generation failed: {exc}*\n\nSource notes: {', '.join(notes)}"

        # Write synthesis note
        try:
            import frontmatter
            from engine.capture import write_note_atomic

            now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
            slug = topic.lower().replace(" ", "-").replace("/", "-")[:40]
            week_str = now.strftime("%Y-%m-%d")
            filename = f"{slug}-{week_str}.md"
            target = BRAIN_ROOT / "syntheses" / filename
            target.parent.mkdir(parents=True, exist_ok=True)

            people = cluster["shared_people"]
            tags = cluster["shared_tags"] + ["auto-synthesized"]

            post = frontmatter.Post(
                synthesis_body,
                title=f"{topic} — Week of {week_str}",
                type="synthesis",
                tags=tags,
                people=people,
                source_notes=notes,
                created_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                updated_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                sensitivity="internal",
            )
            write_note_atomic(target, post, conn)
            stats["syntheses_created"] += 1
            logger.info("Created synthesis: %s", target)
        except Exception as exc:
            logger.warning("Failed to write synthesis note for %s: %s", topic, exc)

    return stats


def consolidate_main() -> None:
    """Entry point for sb-consolidate launchd job. Per D-16 order."""
    # Lazy imports: deferred to avoid slow module-level load of brain_health
    # (heavy dependencies). Reason is startup performance, not import ordering.
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

        # Synthesis phase — must not break hygiene
        try:
            results["synthesis"] = synthesize_clusters(conn)
        except Exception as exc:
            logger.warning("Synthesis phase failed: %s", exc)
            results["synthesis"] = {"error": str(exc)}
    finally:
        conn.close()

    # Log to stdout — captured by launchd StandardOutPath
    print(json.dumps({"at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat(), **results}))
