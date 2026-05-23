from whistle_index.pipeline.run_one_game import run

import argparse


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Whistle Index data engine entrypoint.")
    parser.add_argument("--game-id", dest="game_id", help="Explicit NBA GAME_ID to ingest")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(game_id=args.game_id)
