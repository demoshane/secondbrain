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


def enrichment_sweep(conn) -> dict:
    """Find note pairs with similarity 0.80-0.92 and queue as enrichment candidates.

    Returns: {"queued": int, "scanned": int}
    """
    from engine.intelligence import find_similar

    rows = conn.execute(
        "SELECT note_path FROM note_embeddings ORDER BY rowid DESC LIMIT 500"
    ).fetchall()

    queued = 0
    scanned = 0
    seen_pairs = set()

    for (path,) in rows:
        scanned += 1
        try:
            matches = find_similar(path, conn, threshold=0.72, limit=5)
        except Exception:
            continue

        for m in matches:
            sim = m["similarity"]
            if sim >= 0.92:
                continue

            pair_key = tuple(sorted([path, m["note_path"]]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            source_json = json.dumps(list(pair_key))
            existing = conn.execute(
                "SELECT id FROM consolidation_queue WHERE source_paths = ? AND status IN ('pending', 'dismissed')",
                (source_json,),
            ).fetchone()
            if existing:
                continue

            conn.execute(
                "INSERT INTO consolidation_queue (action, source_paths, reason, similarity, detected_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                ("enrich", source_json, "embedding_similarity", sim),
            )
            queued += 1

    conn.commit()
    return {"queued": queued, "scanned": scanned}


def stale_review(conn) -> dict:
    """Queue notes older than 90 days with low access for review.

    Returns: {"queued": int, "scanned": int}
    """
    stale_rows = conn.execute("""
        SELECT n.path, n.title, n.updated_at
        FROM notes n
        WHERE date(n.updated_at) < date('now', '-90 days')
          AND (n.access_count IS NULL OR n.access_count < 3)
          AND n.path NOT IN (
              SELECT json_each.value FROM consolidation_queue cq,
              json_each(cq.source_paths)
              WHERE cq.action = 'stale' AND cq.status IN ('pending', 'dismissed')
          )
        ORDER BY n.updated_at ASC
        LIMIT 50
    """).fetchall()

    queued = 0
    for path, title, updated_at in stale_rows:
        conn.execute(
            "INSERT INTO consolidation_queue (action, source_paths, reason, detected_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            ("stale", json.dumps([path]), f"Not updated since {updated_at}, low access"),
        )
        queued += 1

    conn.commit()
    return {"queued": queued, "scanned": len(stale_rows)}


def backlink_repair(conn) -> dict:
    """Repair dead wiki-links caused by note merges. Scoped to last 7 days.

    Returns: {"repaired_links": int, "repaired_synthesis_refs": int, "merges_checked": int}
    """
    import frontmatter as _fm
    from engine.paths import BRAIN_ROOT

    merge_rows = conn.execute(
        "SELECT note_path, detail FROM audit_log "
        "WHERE event_type = 'merge' AND created_at > datetime('now', '-7 days')"
    ).fetchall()

    repaired_links = 0
    repaired_synth = 0

    for kept_path, detail in merge_rows:
        if not detail or not detail.startswith("merged:"):
            continue
        discard_path = detail[len("merged:"):]

        body_rows = conn.execute(
            "SELECT path, body FROM notes WHERE body LIKE ?",
            (f"%[[{discard_path}]]%",),
        ).fetchall()

        for note_path, body in body_rows:
            if not body or f"[[{discard_path}]]" not in body:
                continue
            new_body = body.replace(f"[[{discard_path}]]", f"[[{kept_path}]]")
            conn.execute("UPDATE notes SET body=? WHERE path=?", (new_body, note_path))

            note_file = BRAIN_ROOT / note_path
            if note_file.exists():
                try:
                    npost = _fm.load(str(note_file))
                    npost.content = new_body
                    with open(note_file, "w", encoding="utf-8") as fh:
                        fh.write(_fm.dumps(npost))
                except Exception:
                    pass
            repaired_links += 1

        synth_rows = conn.execute(
            "SELECT path FROM notes WHERE type = 'synthesis' LIMIT 200"
        ).fetchall()
        for (synth_path,) in synth_rows:
            synth_file = BRAIN_ROOT / synth_path
            if not synth_file.exists():
                continue
            try:
                spost = _fm.load(str(synth_file))
                sources = spost.get("source_notes", []) or []
                if discard_path in sources:
                    spost["source_notes"] = [kept_path if s == discard_path else s for s in sources]
                    with open(synth_file, "w", encoding="utf-8") as fh:
                        fh.write(_fm.dumps(spost))
                    repaired_synth += 1
            except Exception:
                pass

    conn.commit()
    return {
        "repaired_links": repaired_links,
        "repaired_synthesis_refs": repaired_synth,
        "merges_checked": len(merge_rows),
    }


def consolidate_main() -> None:
    """Entry point for sb-consolidate launchd job. Per D-16 order."""
    # Lazy imports: deferred to avoid slow module-level load of brain_health
    # (heavy dependencies). Reason is startup performance, not import ordering.
    from engine.db import get_connection, init_schema, record_job_start, record_job_finish
    from engine.brain_health import (
        archive_old_action_items,
        archive_old_audit_entries,
        delete_dangling_relationships,
        take_health_snapshot,
        cleanup_old_snapshots,
    )

    conn = get_connection()
    init_schema(conn)
    job_id = record_job_start(conn, "consolidate")
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

        # Phase 57: enrichment sweep, stale review, backlink repair
        try:
            results["enrichment_sweep"] = enrichment_sweep(conn)
        except Exception as exc:
            logger.warning("Enrichment sweep failed: %s", exc)
            results["enrichment_sweep"] = {"error": str(exc)}

        try:
            results["stale_review"] = stale_review(conn)
        except Exception as exc:
            logger.warning("Stale review failed: %s", exc)
            results["stale_review"] = {"error": str(exc)}

        try:
            results["backlink_repair"] = backlink_repair(conn)
        except Exception as exc:
            logger.warning("Backlink repair failed: %s", exc)
            results["backlink_repair"] = {"error": str(exc)}
    finally:
        conn.close()

    # Performance benchmarks — runs after DB is closed (uses its own connections)
    try:
        from engine.perf import run_benchmarks
        bench = run_benchmarks()
        results["perf"] = {"tools_tested": len(bench.get("results", [])), "stored": True}
    except Exception as exc:
        logger.warning("Perf benchmarks failed: %s", exc)
        results["perf"] = {"error": str(exc)}

    # Record job completion
    try:
        _finish_conn = get_connection()
        try:
            record_job_finish(_finish_conn, job_id, "success", json.dumps({k: str(v)[:100] for k, v in results.items()}))
        finally:
            _finish_conn.close()
    except Exception:
        pass

    # Log to stdout — captured by launchd StandardOutPath
    print(json.dumps({"at": datetime.datetime.now(datetime.UTC).replace(tzinfo=None).isoformat(), **results}))
