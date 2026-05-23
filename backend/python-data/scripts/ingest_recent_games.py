from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

from nba_api.stats.endpoints import ScoreboardV3

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from whistle_index.pipeline.run_one_game import run  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest and score recent completed NBA games into local artifacts."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="How many recent days to scan for completed games.",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=15,
        help="Max number of games to process.",
    )
    return parser.parse_args()


def _scoreboard_with_retry(date_str: str, timeout: int = 30, retries: int = 3) -> dict:
    """Fetch ScoreboardV3 for a single date, retrying on timeout/network errors."""
    for attempt in range(1, retries + 1):
        try:
            return ScoreboardV3(game_date=date_str, timeout=timeout).get_dict()
        except Exception as exc:
            if attempt == retries:
                raise
            wait = 2 ** attempt  # 2s, 4s, ...
            print(f"  ScoreboardV3 failed ({exc.__class__.__name__}), retry {attempt}/{retries - 1} in {wait}s…")
            time.sleep(wait)
    return {}  # unreachable


def collect_recent_completed_game_ids(days: int, max_games: int) -> list[str]:
    game_ids: list[str] = []
    seen: set[str] = set()

    for offset in range(days + 1):
        day = datetime.now(UTC) - timedelta(days=offset)
        payload = _scoreboard_with_retry(day.strftime("%m/%d/%Y"))
        time.sleep(0.6)  # stay well under stats.nba.com rate limit
        games = payload.get("scoreboard", {}).get("games", [])
        for game in games:
            if game.get("gameStatus") != 3:
                continue
            game_id = str(game.get("gameId") or "")
            if not game_id or game_id in seen:
                continue
            seen.add(game_id)
            game_ids.append(game_id)
            if len(game_ids) >= max_games:
                return game_ids

    return game_ids


def _already_ingested(game_id: str) -> bool:
    scored_path = ROOT / "artifacts" / "scored" / f"{game_id}.json"
    return scored_path.exists()


def main() -> None:
    args = parse_args()
    game_ids = collect_recent_completed_game_ids(args.days, args.max_games)
    print(f"Found {len(game_ids)} completed games to process")

    new_ids = [gid for gid in game_ids if not _already_ingested(gid)]
    skipped = len(game_ids) - len(new_ids)
    if skipped:
        print(f"Skipping {skipped} already-ingested game(s)")

    failed: list[str] = []
    for idx, game_id in enumerate(new_ids, start=1):
        print(f"[{idx}/{len(new_ids)}] Processing game {game_id}")
        try:
            run(game_id=game_id)
        except Exception as exc:
            print(f"  ERROR processing {game_id}: {exc.__class__.__name__}: {exc} — skipping")
            failed.append(game_id)

    if failed:
        print(f"\nFailed games ({len(failed)}): {', '.join(failed)}")
    if not new_ids:
        print("No new completed games to ingest.")


if __name__ == "__main__":
    main()
