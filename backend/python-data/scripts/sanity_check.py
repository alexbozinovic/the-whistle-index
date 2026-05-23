from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _team_map(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        team_id = row.get("team_id")
        if team_id is not None:
            out[int(team_id)] = row
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one-game Whistle Index artifacts.")
    parser.add_argument("--game-id", required=True, help="NBA game id")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Root artifacts directory (default: artifacts)",
    )
    parser.add_argument(
        "--foul-tolerance",
        type=int,
        default=6,
        help="Allowed absolute delta between parsed fouls and boxscore PF.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = Path(args.artifacts_dir)

    raw = _load_json(base / "raw" / f"{args.game_id}.json")
    parsed = _load_json(base / "parsed" / f"{args.game_id}.json")
    scored = _load_json(base / "scored" / f"{args.game_id}.json")

    failures: list[str] = []
    warnings: list[str] = []

    game = raw.get("game", {})
    if str(game.get("game_id")) != args.game_id:
        failures.append("Raw artifact game_id mismatch")
    if str(parsed.get("game_id")) != args.game_id:
        failures.append("Parsed artifact game_id mismatch")
    if str(scored.get("game_id")) != args.game_id:
        failures.append("Scored artifact game_id mismatch")

    team_rows = parsed.get("team_breakdown", [])
    if len(team_rows) < 2:
        failures.append("Parsed team_breakdown must have at least 2 rows")

    teams = _team_map(team_rows)
    home_id = game.get("home_team_id")
    away_id = game.get("away_team_id")
    if home_id is None or away_id is None:
        failures.append("Missing home/away team ids in raw game")

    if home_id is not None and away_id is not None:
        home = teams.get(int(home_id), {})
        away = teams.get(int(away_id), {})
        if not home or not away:
            failures.append("Missing home or away team rows in parsed breakdown")
        else:
            for label, row in [("home", home), ("away", away)]:
                parsed_fta = int(row.get("parsed_free_throw_attempts") or 0)
                box_fta = int(row.get("boxscore_fta") or 0)
                if parsed_fta != box_fta:
                    failures.append(
                        f"{label} free-throw mismatch parsed={parsed_fta} box={box_fta}"
                    )

                parsed_pf = int(row.get("parsed_fouls_called") or 0)
                box_pf = int(row.get("boxscore_pf") or 0)
                pf_delta = abs(parsed_pf - box_pf)
                if pf_delta > args.foul_tolerance:
                    failures.append(
                        f"{label} foul delta too large parsed={parsed_pf} box={box_pf} delta={pf_delta}"
                    )
                elif pf_delta > 0:
                    warnings.append(
                        f"{label} foul delta observed parsed={parsed_pf} box={box_pf} delta={pf_delta}"
                    )

            diff = parsed.get("differential_primitives", {})
            home_away_fouls = int(home.get("parsed_fouls_called") or 0) - int(
                away.get("parsed_fouls_called") or 0
            )
            home_away_fta = int(home.get("parsed_free_throw_attempts") or 0) - int(
                away.get("parsed_free_throw_attempts") or 0
            )
            if home_away_fouls != int(diff.get("home_minus_away_fouls_called") or 0):
                failures.append("Differential mismatch for home_minus_away_fouls_called")
            if home_away_fta != int(diff.get("home_minus_away_free_throw_attempts") or 0):
                failures.append("Differential mismatch for home_minus_away_free_throw_attempts")

    scores = scored.get("scores", {})
    for key in [
        "crew_impact_score",
        "home_whistle_score",
        "game_control_score",
        "clutch_influence_score",
    ]:
        if key not in scores:
            failures.append(f"Missing scored metric: {key}")

    drivers = scored.get("main_drivers", [])
    if not isinstance(drivers, list) or len(drivers) < 1:
        failures.append("Expected at least one main driver in scored artifact")

    print(f"Sanity check for game {args.game_id}")
    print(f"Raw artifact: {base / 'raw' / f'{args.game_id}.json'}")
    print(f"Parsed artifact: {base / 'parsed' / f'{args.game_id}.json'}")
    print(f"Scored artifact: {base / 'scored' / f'{args.game_id}.json'}")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("All acceptance checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
