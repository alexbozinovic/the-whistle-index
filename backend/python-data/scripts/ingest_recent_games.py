from __future__ import annotations

import argparse
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


def collect_recent_completed_game_ids(days: int, max_games: int) -> list[str]:
    game_ids: list[str] = []
    seen: set[str] = set()

    for offset in range(days + 1):
        day = datetime.now(UTC) - timedelta(days=offset)
        payload = ScoreboardV3(
            game_date=day.strftime("%m/%d/%Y"),
            timeout=30,
        ).get_dict()
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


def main() -> None:
    args = parse_args()
    game_ids = collect_recent_completed_game_ids(args.days, args.max_games)
    print(f"Found {len(game_ids)} completed games to process")

    for idx, game_id in enumerate(game_ids, start=1):
        print(f"[{idx}/{len(game_ids)}] Processing game {game_id}")
        run(game_id=game_id)

    if not game_ids:
        print("No completed games found for the selected window.")


if __name__ == "__main__":
    main()
