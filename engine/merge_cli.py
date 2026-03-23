"""Interactive CLI for merging duplicate notes.

Entry point: sb-merge-duplicates (registered in pyproject.toml).
Prompts user through each duplicate candidate pair, calls merge_notes().
"""
from __future__ import annotations


def merge_duplicates_main() -> None:
    """Interactive CLI: review duplicate pairs and merge or skip each one."""
    from engine.db import get_connection, init_schema
    from engine.brain_health import get_duplicate_candidates, merge_notes

    conn = get_connection()
    init_schema(conn)
    try:
        pairs = get_duplicate_candidates(conn)
        if not pairs:
            print("No duplicate candidates found.")
            return
        print(f"Found {len(pairs)} duplicate candidate(s).\n")
        for i, pair in enumerate(pairs, 1):
            print(f"--- Pair {i}/{len(pairs)} (similarity: {pair['similarity']:.2%}) ---")
            print(f"  A: {pair['a']}")
            print(f"  B: {pair['b']}")
            choice = input("  Merge? [a=keep A, b=keep B, s=skip]: ").strip().lower()
            if choice == "a":
                result = merge_notes(pair["a"], pair["b"], conn)
                print(f"  Merged: kept {result['keep']}, discarded {result['discarded']}")
            elif choice == "b":
                result = merge_notes(pair["b"], pair["a"], conn)
                print(f"  Merged: kept {result['keep']}, discarded {result['discarded']}")
            else:
                print("  Skipped.")
        print("\nDone.")
    finally:
        conn.close()
