"""
Ingest a batch of 2023-24 regular-season games that have L2M reports.
Reads the cached L2M CSV, picks the first --count unique game IDs not yet
in artifacts/raw/, and runs the standard pipeline for each.

Usage:
    python scripts/ingest_l2m_games.py            # ingest 5 games
    python scripts/ingest_l2m_games.py --count 10
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from whistle_index.pipeline.run_one_game import run  # noqa: E402

L2M_CSV = ROOT / "data" / "l2m_2023_24.csv"
RAW_DIR = ROOT / "artifacts" / "raw"


def _l2m_game_ids() -> list[str]:
    """Return unique game IDs from the CSV, preserving order of first appearance."""
    if not L2M_CSV.exists():
        raise FileNotFoundError(
            f"L2M CSV not found at {L2M_CSV}. Run scripts/fetch_l2m_csv.py first."
        )
    seen: list[str] = []
    visited: set[str] = set()
    with L2M_CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            gid = row.get("game_id", "").replace("gameId=", "").strip()
            if gid and gid not in visited:
                visited.add(gid)
                seen.append(gid)
    return seen


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest L2M-tracked 2023-24 games.")
    parser.add_argument("--count", type=int, default=5, help="Number of games to ingest (default 5)")
    args = parser.parse_args()

    all_ids = _l2m_game_ids()
    already_done = {p.stem for p in RAW_DIR.glob("*.json")} if RAW_DIR.exists() else set()
    todo = [gid for gid in all_ids if gid not in already_done][: args.count]

    if not todo:
        print("Nothing to ingest — all L2M games already present in artifacts/raw/.")
        return

    print(f"Ingesting {len(todo)} games: {todo}")
    failed: list[str] = []

    for i, gid in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {gid} …")
        try:
            run(game_id=gid)
            time.sleep(1.5)  # be polite to the API
        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed.append(gid)

    print(f"\nDone. ingested={len(todo) - len(failed)}  failed={len(failed)}")
    if failed:
        print(f"  failed IDs: {failed}")


if __name__ == "__main__":
    main()
