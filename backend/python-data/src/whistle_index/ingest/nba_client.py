from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any

from nba_api.stats.endpoints import (
    BoxScoreSummaryV3,
    BoxScoreSummaryV2,
    BoxScoreTraditionalV2,
    PlayByPlayV3,
    PlayByPlayV2,
    ScoreboardV3,
)


def _with_retry(fn, *, retries: int = 3):
    """Call fn(), retrying on any exception with exponential backoff."""
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries:
                raise
            wait = 2 ** attempt
            print(f"  API call failed ({exc.__class__.__name__}), retry {attempt}/{retries - 1} in {wait}s…")
            time.sleep(wait)


class NBAIngestionClient:
    """Fetches one-game datasets from public NBA endpoints."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def find_recent_completed_game(
        self,
        *,
        max_lookback_days: int = 14,
        from_date: datetime | None = None,
    ) -> str:
        """Return the latest completed game id by scanning backward from a date."""
        scan_date = from_date or datetime.now(UTC)

        for day_offset in range(max_lookback_days + 1):
            query_date = scan_date - timedelta(days=day_offset)
            scoreboard = ScoreboardV3(
                game_date=query_date.strftime("%m/%d/%Y"),
                timeout=self.timeout,
            )
            games = scoreboard.get_dict().get("scoreboard", {}).get("games", [])
            completed = [
                row for row in games if row.get("gameStatus") == 3 and row.get("gameId")
            ]
            if completed:
                completed.sort(key=lambda row: row.get("gameTimeUTC", ""), reverse=True)
                return str(completed[0]["gameId"])

        raise RuntimeError(
            f"No completed NBA game found in the last {max_lookback_days} days."
        )

    def fetch_game_package(self, game_id: str) -> dict[str, Any]:
        """Fetch all step-2 datasets for one game id."""
        traditional = _with_retry(
            lambda: BoxScoreTraditionalV2(game_id=game_id, timeout=self.timeout)
        )

        summary_v3: dict[str, Any] = {}
        summary_v2: dict[str, Any] = {}
        play_by_play_v3: dict[str, Any] = {}
        play_by_play_v2: dict[str, Any] = {}

        try:
            summary_v3 = BoxScoreSummaryV3(game_id=game_id, timeout=self.timeout).get_dict()
        except Exception:
            summary_v3 = {}

        if not summary_v3:
            try:
                summary_v2 = BoxScoreSummaryV2(
                    game_id=game_id, timeout=self.timeout
                ).get_normalized_dict()
            except Exception:
                summary_v2 = {}

        try:
            play_by_play_v3 = PlayByPlayV3(game_id=game_id, timeout=self.timeout).get_dict()
        except Exception:
            play_by_play_v3 = {}

        if not play_by_play_v3:
            try:
                play_by_play_v2 = PlayByPlayV2(
                    game_id=game_id, timeout=self.timeout
                ).get_normalized_dict()
            except Exception:
                play_by_play_v2 = {}

        return {
            "game_id": game_id,
            "fetched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "box_score_traditional": traditional.get_normalized_dict(),
            "box_score_summary_v2": summary_v2,
            "box_score_summary_v3": summary_v3,
            "play_by_play_v2": play_by_play_v2,
            "play_by_play_v3": play_by_play_v3,
        }
