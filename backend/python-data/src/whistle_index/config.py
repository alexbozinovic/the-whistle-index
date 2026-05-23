from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    bq_dataset: str = os.getenv("BQ_DATASET", "whistle_index")
    google_application_credentials: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    nba_season: str = os.getenv("NBA_SEASON", "2025-26")
    default_game_id: str = os.getenv("DEFAULT_GAME_ID", "")
    game_lookup_lookback_days: int = int(os.getenv("GAME_LOOKBACK_DAYS", "14"))
    nba_request_timeout: int = int(os.getenv("NBA_REQUEST_TIMEOUT", "30"))
    raw_output_dir: str = os.getenv("RAW_OUTPUT_DIR", "artifacts/raw")
    parsed_output_dir: str = os.getenv("PARSED_OUTPUT_DIR", "artifacts/parsed")
    scored_output_dir: str = os.getenv("SCORED_OUTPUT_DIR", "artifacts/scored")
    bigquery_write_enabled: bool = os.getenv("BIGQUERY_WRITE_ENABLED", "true").lower() in {
        "1",
        "true",
        "yes",
    }


def get_settings() -> Settings:
    return Settings()
