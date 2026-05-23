from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from google.cloud import bigquery


@dataclass(frozen=True)
class BigQueryLoadResult:
    dataset_id: str
    game_id: str
    rows_written: dict[str, int]


class BigQueryLoader:
    def __init__(self, project_id: str, dataset: str) -> None:
        if not project_id:
            raise ValueError("GCP project id is required for BigQuery loading.")
        if not dataset:
            raise ValueError("BigQuery dataset is required.")

        self.project_id = project_id
        self.dataset = dataset
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = f"{project_id}.{dataset}"

    def ensure_schema(self) -> None:
        dataset_ref = bigquery.Dataset(self.dataset_id)
        dataset_ref.location = "US"
        self.client.create_dataset(dataset_ref, exists_ok=True)

        table_specs: list[tuple[str, list[bigquery.SchemaField]]] = [
            (
                "games",
                [
                    bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("season", "STRING"),
                    bigquery.SchemaField("game_date_est", "TIMESTAMP"),
                    bigquery.SchemaField("home_team_id", "INT64"),
                    bigquery.SchemaField("away_team_id", "INT64"),
                    bigquery.SchemaField("home_team_abbreviation", "STRING"),
                    bigquery.SchemaField("away_team_abbreviation", "STRING"),
                    bigquery.SchemaField("home_score", "INT64"),
                    bigquery.SchemaField("away_score", "INT64"),
                    bigquery.SchemaField("arena", "STRING"),
                    bigquery.SchemaField("attendance", "INT64"),
                    bigquery.SchemaField("game_status_text", "STRING"),
                    bigquery.SchemaField("created_at", "TIMESTAMP"),
                ],
            ),
            (
                "referees",
                [
                    bigquery.SchemaField("referee_id", "INT64", mode="REQUIRED"),
                    bigquery.SchemaField("first_name", "STRING"),
                    bigquery.SchemaField("last_name", "STRING"),
                    bigquery.SchemaField("jersey_num", "STRING"),
                    bigquery.SchemaField("active_status", "BOOL"),
                    bigquery.SchemaField("updated_at", "TIMESTAMP"),
                ],
            ),
            (
                "game_referees",
                [
                    bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("referee_id", "INT64", mode="REQUIRED"),
                    bigquery.SchemaField("role", "STRING"),
                    bigquery.SchemaField("crew_id", "STRING"),
                    bigquery.SchemaField("created_at", "TIMESTAMP"),
                ],
            ),
            (
                "team_game_stats",
                [
                    bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("team_id", "INT64", mode="REQUIRED"),
                    bigquery.SchemaField("opponent_team_id", "INT64"),
                    bigquery.SchemaField("team_abbreviation", "STRING"),
                    bigquery.SchemaField("is_home", "BOOL"),
                    bigquery.SchemaField("free_throw_attempts", "INT64"),
                    bigquery.SchemaField("personal_fouls", "INT64"),
                    bigquery.SchemaField("fourth_quarter_fouls_called", "INT64"),
                    bigquery.SchemaField("fourth_quarter_free_throw_attempts", "INT64"),
                    bigquery.SchemaField("clutch_fouls_called", "INT64"),
                    bigquery.SchemaField("clutch_free_throw_attempts", "INT64"),
                    bigquery.SchemaField("created_at", "TIMESTAMP"),
                ],
            ),
            (
                "referee_game_scores",
                [
                    bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("referee_id", "INT64", mode="REQUIRED"),
                    bigquery.SchemaField("crew_id", "STRING"),
                    bigquery.SchemaField("impact_score", "FLOAT64"),
                    bigquery.SchemaField("home_whistle_score", "FLOAT64"),
                    bigquery.SchemaField("game_control_score", "FLOAT64"),
                    bigquery.SchemaField("clutch_influence_score", "FLOAT64"),
                    bigquery.SchemaField("home_team_lean_points", "FLOAT64"),
                    bigquery.SchemaField("away_team_lean_points", "FLOAT64"),
                    bigquery.SchemaField("favored_team_id", "INT64"),
                    bigquery.SchemaField("favored_team_abbreviation", "STRING"),
                    bigquery.SchemaField("created_at", "TIMESTAMP"),
                ],
            ),
        ]

        for table_name, schema in table_specs:
            table_id = f"{self.dataset_id}.{table_name}"
            self.client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)

    def load_game_bundle(
        self,
        *,
        normalized: dict[str, Any],
        parsed: dict[str, Any],
        scored: dict[str, Any],
        season_fallback: str,
    ) -> BigQueryLoadResult:
        self.ensure_schema()

        game = normalized.get("game", {})
        game_id = str(game.get("game_id") or "")
        if not game_id:
            raise ValueError("game_id is required for BigQuery load.")

        now_iso = datetime.now(UTC).isoformat(timespec="seconds")
        officials = normalized.get("officials", [])
        crew_ids = sorted(
            int(ref.get("official_id"))
            for ref in officials
            if ref.get("official_id") is not None
        )
        crew_id = "-".join(str(ref_id) for ref_id in crew_ids) if crew_ids else None

        home_team_id = game.get("home_team_id")
        away_team_id = game.get("away_team_id")

        team_breakdown_map = {
            int(row.get("team_id")): row
            for row in parsed.get("team_breakdown", [])
            if row.get("team_id") is not None
        }

        game_row = {
            "game_id": game_id,
            "season": game.get("season") or season_fallback,
            "game_date_est": game.get("game_date_est"),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_abbreviation": game.get("home_team_abbreviation"),
            "away_team_abbreviation": game.get("away_team_abbreviation"),
            "home_score": game.get("home_score"),
            "away_score": game.get("away_score"),
            "arena": game.get("arena"),
            "attendance": game.get("attendance"),
            "game_status_text": game.get("game_status_text"),
            "created_at": now_iso,
        }

        referee_rows = [
            {
                "referee_id": int(ref.get("official_id")),
                "first_name": ref.get("first_name"),
                "last_name": ref.get("last_name"),
                "jersey_num": (ref.get("jersey_num") or "").strip() or None,
                "active_status": True,
                "updated_at": now_iso,
            }
            for ref in officials
            if ref.get("official_id") is not None
        ]

        game_ref_rows = [
            {
                "game_id": game_id,
                "referee_id": int(ref.get("official_id")),
                "role": "crew",
                "crew_id": crew_id,
                "created_at": now_iso,
            }
            for ref in officials
            if ref.get("official_id") is not None
        ]

        team_rows: list[dict[str, Any]] = []
        for team_id in [home_team_id, away_team_id]:
            if team_id is None:
                continue
            row = team_breakdown_map.get(int(team_id), {})
            is_home = int(team_id) == int(home_team_id)
            opponent_team_id = away_team_id if is_home else home_team_id
            team_rows.append(
                {
                    "game_id": game_id,
                    "team_id": int(team_id),
                    "opponent_team_id": int(opponent_team_id) if opponent_team_id is not None else None,
                    "team_abbreviation": row.get("team_abbreviation"),
                    "is_home": is_home,
                    "free_throw_attempts": row.get("parsed_free_throw_attempts"),
                    "personal_fouls": row.get("parsed_fouls_called"),
                    "fourth_quarter_fouls_called": row.get("parsed_fourth_quarter_fouls_called"),
                    "fourth_quarter_free_throw_attempts": row.get(
                        "parsed_fourth_quarter_free_throw_attempts"
                    ),
                    "clutch_fouls_called": row.get("parsed_clutch_fouls_called"),
                    "clutch_free_throw_attempts": row.get("parsed_clutch_free_throw_attempts"),
                    "created_at": now_iso,
                }
            )

        score_rows = [
            {
                "game_id": game_id,
                "referee_id": int(ref.get("official_id")),
                "crew_id": crew_id,
                "impact_score": scored.get("scores", {}).get("crew_impact_score"),
                "home_whistle_score": scored.get("scores", {}).get("home_whistle_score"),
                "game_control_score": scored.get("scores", {}).get("game_control_score"),
                "clutch_influence_score": scored.get("scores", {}).get("clutch_influence_score"),
                "home_team_lean_points": scored.get("team_whistle_lean", {}).get(
                    "home_team_lean_points"
                ),
                "away_team_lean_points": scored.get("team_whistle_lean", {}).get(
                    "away_team_lean_points"
                ),
                "favored_team_id": scored.get("team_whistle_lean", {}).get("favored_team_id"),
                "favored_team_abbreviation": scored.get("team_whistle_lean", {}).get(
                    "favored_team_abbreviation"
                ),
                "created_at": now_iso,
            }
            for ref in officials
            if ref.get("official_id") is not None
        ]

        # Idempotent by game id for game-scoped tables.
        for table_name in ["games", "game_referees", "team_game_stats", "referee_game_scores"]:
            query = f"DELETE FROM `{self.dataset_id}.{table_name}` WHERE game_id = @game_id"
            job_config = bigquery.QueryJobConfig(
                query_parameters=[bigquery.ScalarQueryParameter("game_id", "STRING", game_id)]
            )
            self.client.query(query, job_config=job_config).result()

        if referee_rows:
            referee_ids = [row["referee_id"] for row in referee_rows]
            query = (
                f"DELETE FROM `{self.dataset_id}.referees` "
                "WHERE referee_id IN UNNEST(@referee_ids)"
            )
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("referee_ids", "INT64", referee_ids)
                ]
            )
            self.client.query(query, job_config=job_config).result()

        self._insert_rows("games", [game_row])
        self._insert_rows("referees", referee_rows)
        self._insert_rows("game_referees", game_ref_rows)
        self._insert_rows("team_game_stats", team_rows)
        self._insert_rows("referee_game_scores", score_rows)

        return BigQueryLoadResult(
            dataset_id=self.dataset_id,
            game_id=game_id,
            rows_written={
                "games": 1,
                "referees": len(referee_rows),
                "game_referees": len(game_ref_rows),
                "team_game_stats": len(team_rows),
                "referee_game_scores": len(score_rows),
            },
        )

    def _insert_rows(self, table_name: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return

        table_id = f"{self.dataset_id}.{table_name}"
        errors = self.client.insert_rows_json(table_id, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert failed for {table_name}: {errors}")
