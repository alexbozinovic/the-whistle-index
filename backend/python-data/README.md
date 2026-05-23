# Python Data Engine

This package powers data ingestion, parsing, scoring, and warehouse loading for The Whistle Index.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

3. Copy environment template:

   cp .env.example .env

4. Run the pipeline placeholder:

   python -m src.main

## Scripts

Setup environment and install dependencies:

   scripts/setup_env.sh

Run pipeline (auto game selection):

   scripts/run_pipeline.sh

Run pipeline for a specific game id:

   scripts/run_pipeline.sh --game-id 0042500313

Verify BigQuery rows for a loaded game:

   source .venv/bin/activate
   python scripts/verify_bigquery.py --project-id <project> --dataset <dataset> --game-id <game_id>

Run local artifact sanity checks for a game:

   source .venv/bin/activate
   python scripts/sanity_check.py --game-id 0042500313

Run end-to-end acceptance in one command:

   scripts/run_acceptance.sh 0042500313

## Step 2 ingestion

Run one-game ingestion with automatic game discovery:

   python -m src.main

Run one-game ingestion with an explicit game id:

   python -m src.main --game-id 0022300061

Expected output:

- Latest completed game id (or provided id)
- Game metadata and final score
- Referee list count
- Team stats row count
- Play-by-play row count
- JSON artifact under artifacts/raw/<game_id>.json

Step 3 parsed output:

- Whistle event extraction (fouls and free throws)
- Fourth-quarter and clutch tags per event
- Home-away differential primitives for fouls and free throw attempts
- JSON artifact under artifacts/parsed/<game_id>.json

Step 4 scoring output:

- Equal-weight MVP score model
- Crew Impact Score
- Home Whistle Score
- Game Control Score
- Clutch Influence Score
- Team whistle lean points for home and away sides
- Plain-English main drivers from score components
- JSON artifact under artifacts/scored/<game_id>.json

Step 5 BigQuery load:

- Ensures dataset and MVP tables exist:
   - games
   - referees
   - game_referees
   - team_game_stats
   - referee_game_scores
- Performs idempotent game-scoped writes (re-running same game replaces prior rows)
- Loads from in-memory normalized, parsed, and scored bundles in one run

Enable BigQuery writes by setting:

- GCP_PROJECT_ID
- BQ_DATASET
- GOOGLE_APPLICATION_CREDENTIALS
- BIGQUERY_WRITE_ENABLED=true

## Step 7 hardening checklist

- Pipeline runs end-to-end for one game id
- Raw, parsed, and scored artifacts are generated
- Parsed free throws match box score by team
- Parsed foul deltas stay within tolerance and are surfaced as warnings
- Differential primitives reconcile with parsed team totals
- Scored artifact includes all core MVP metrics and main drivers
- Optional: BigQuery row counts verified with scripts/verify_bigquery.py

## Planned modules

- ingest: NBA data retrieval
- parse: play-by-play parsing and feature extraction
- scoring: metric computations
- storage: BigQuery persistence
- pipeline: end-to-end orchestration
