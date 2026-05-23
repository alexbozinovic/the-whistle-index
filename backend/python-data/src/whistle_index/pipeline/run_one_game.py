from __future__ import annotations

import argparse
import json
from pathlib import Path

from whistle_index.config import get_settings
from whistle_index.ingest.nba_client import NBAIngestionClient
from whistle_index.ingest.normalize import normalize_game_package
from whistle_index.l2m.parse_l2m import parse_l2m
from whistle_index.parse.play_by_play_parser import extract_whistle_features
from whistle_index.scoring.mvp_scores import compute_mvp_scores
from whistle_index.storage.bigquery_loader import BigQueryLoader

_ROOT = Path(__file__).resolve().parents[3]  # backend/python-data
_L2M_CSV = _ROOT / "data" / "l2m_2023_24.csv"


def _artifact_path(base_dir: str, game_id: str) -> Path:
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{game_id}.json"


def run(game_id: str | None = None) -> None:
    settings = get_settings()
    client = NBAIngestionClient(timeout=settings.nba_request_timeout)

    resolved_game_id = game_id or settings.default_game_id
    if not resolved_game_id:
        resolved_game_id = client.find_recent_completed_game(
            max_lookback_days=settings.game_lookup_lookback_days
        )

    raw_package = client.fetch_game_package(resolved_game_id)
    normalized = normalize_game_package(raw_package)
    parsed = extract_whistle_features(normalized)
    scored = compute_mvp_scores(normalized, parsed)

    raw_artifact_path = _artifact_path(settings.raw_output_dir, resolved_game_id)
    raw_artifact_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

    parsed_artifact_path = _artifact_path(settings.parsed_output_dir, resolved_game_id)
    parsed_artifact_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")

    scored_artifact_path = _artifact_path(settings.scored_output_dir, resolved_game_id)
    scored_artifact_path.write_text(json.dumps(scored, indent=2), encoding="utf-8")

    # Step 4b: L2M parsing (only when CSV is present and has data for this game)
    l2m_artifact: dict | None = None
    if _L2M_CSV.exists():
        try:
            l2m_result = parse_l2m(
                resolved_game_id,
                csv_path=_L2M_CSV,
                home_team_abbreviation=normalized["game"].get("home_team_abbreviation", ""),
                away_team_abbreviation=normalized["game"].get("away_team_abbreviation", ""),
                timeout=settings.nba_request_timeout,
            )
            if l2m_result["total_events"] > 0:
                l2m_artifact_path = _artifact_path(
                    str(Path(settings.raw_output_dir).parent / "l2m"), resolved_game_id
                )
                l2m_artifact_path.write_text(json.dumps(l2m_result, indent=2), encoding="utf-8")
                l2m_artifact = l2m_result
                print(
                    f"Step 4b L2M parsed: total={l2m_result['total_events']}, "
                    f"incorrect={l2m_result['incorrect_count']}, "
                    f"home_benefit={l2m_result['home_l2m_benefit']}, "
                    f"away_benefit={l2m_result['away_l2m_benefit']}"
                )
                print(f"L2M artifact written: {l2m_artifact_path}")
            else:
                print("Step 4b L2M: no events found for this game (not in 2023-24 CSV).")
        except Exception as exc:
            print(f"Step 4b L2M skipped: {exc}")

    game = normalized["game"]
    _ = l2m_artifact  # available for callers who import run() and inspect returns
    print("Step 2 ingestion completed.")
    print(f"Game id: {game['game_id']}")
    print(
        "Matchup: "
        f"{game.get('away_team_abbreviation') or game.get('away_team_id')} at "
        f"{game.get('home_team_abbreviation') or game.get('home_team_id')}"
    )
    print(f"Final score: {game.get('away_score')} - {game.get('home_score')}")
    print(
        "Rows: "
        f"officials={normalized['counts']['officials']}, "
        f"team_stats={normalized['counts']['team_stats_rows']}, "
        f"play_by_play={normalized['counts']['play_by_play_rows']}"
    )
    print(f"Raw artifact written: {raw_artifact_path}")

    print("Step 3 parsing completed.")
    print(
        "Whistle events: "
        f"total={parsed['parsed_event_counts']['total_whistle_events']}, "
        f"fouls={parsed['parsed_event_counts']['foul_events']}, "
        f"free_throws={parsed['parsed_event_counts']['free_throw_events']}, "
        f"clutch={parsed['parsed_event_counts']['clutch_whistle_events']}"
    )
    print(
        "Differentials (home-away): "
        f"fouls={parsed['differential_primitives']['home_minus_away_fouls_called']}, "
        f"fta={parsed['differential_primitives']['home_minus_away_free_throw_attempts']}, "
        f"4q_fta={parsed['differential_primitives']['home_minus_away_fourth_quarter_free_throw_attempts']}, "
        f"clutch_fta={parsed['differential_primitives']['home_minus_away_clutch_free_throw_attempts']}"
    )
    print(f"Parsed artifact written: {parsed_artifact_path}")

    print("Step 4 scoring completed.")
    print(
        "Scores: "
        f"impact={scored['scores']['crew_impact_score']}, "
        f"home_whistle={scored['scores']['home_whistle_score']}, "
        f"control={scored['scores']['game_control_score']}, "
        f"clutch={scored['scores']['clutch_influence_score']}"
    )
    print(
        "Team whistle lean: "
        f"home={scored['team_whistle_lean']['home_team_lean_points']}, "
        f"away={scored['team_whistle_lean']['away_team_lean_points']}, "
        f"favored={scored['team_whistle_lean']['favored_team_abbreviation']}"
    )
    print("Main drivers:")
    for line in scored["main_drivers"]:
        print(f"- {line}")
    print(f"Scored artifact written: {scored_artifact_path}")

    if not settings.bigquery_write_enabled:
        print("Step 5 BigQuery load skipped: BIGQUERY_WRITE_ENABLED is false.")
        return

    if not settings.gcp_project_id:
        print("Step 5 BigQuery load skipped: GCP_PROJECT_ID is not configured.")
        return

    loader = BigQueryLoader(project_id=settings.gcp_project_id, dataset=settings.bq_dataset)
    load_result = loader.load_game_bundle(
        normalized=normalized,
        parsed=parsed,
        scored=scored,
        season_fallback=settings.nba_season,
    )
    print("Step 5 BigQuery load completed.")
    print(f"Dataset: {load_result.dataset_id}")
    print(
        "Rows written: "
        f"games={load_result.rows_written['games']}, "
        f"referees={load_result.rows_written['referees']}, "
        f"game_referees={load_result.rows_written['game_referees']}, "
        f"team_game_stats={load_result.rows_written['team_game_stats']}, "
        f"referee_game_scores={load_result.rows_written['referee_game_scores']}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one-game NBA ingestion pipeline.")
    parser.add_argument("--game-id", dest="game_id", help="Explicit NBA GAME_ID to ingest")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(game_id=args.game_id)
