from __future__ import annotations

import argparse

from google.cloud import bigquery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify BigQuery load rows for one game."
    )
    parser.add_argument("--project-id", required=True, help="GCP project id")
    parser.add_argument("--dataset", required=True, help="BigQuery dataset name")
    parser.add_argument("--game-id", required=True, help="NBA game id to verify")
    return parser.parse_args()


def fetch_count(client: bigquery.Client, table_ref: str, game_id: str) -> int:
    query = f"SELECT COUNT(1) AS c FROM `{table_ref}` WHERE game_id = @game_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("game_id", "STRING", game_id),
        ]
    )
    rows = list(client.query(query, job_config=job_config).result())
    if not rows:
        return 0
    return int(rows[0]["c"])


def main() -> None:
    args = parse_args()
    client = bigquery.Client(project=args.project_id)
    dataset_id = f"{args.project_id}.{args.dataset}"

    tables = [
        "games",
        "game_referees",
        "team_game_stats",
        "referee_game_scores",
    ]

    print(f"Verifying dataset: {dataset_id}")
    print(f"Game id: {args.game_id}")

    for table in tables:
        table_ref = f"{dataset_id}.{table}"
        count = fetch_count(client, table_ref, args.game_id)
        print(f"{table}: {count}")


if __name__ == "__main__":
    main()
