from __future__ import annotations

from typing import Any


def _find_first(rows: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any] | None:
    for row in rows:
        if row.get(key) == value:
            return row
    return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_game_package(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize raw API payloads into a stable ingestion artifact."""
    summary_v2 = raw.get("box_score_summary_v2", {})
    summary_v3 = raw.get("box_score_summary_v3", {})
    traditional = raw.get("box_score_traditional", {})
    pbp_v2 = raw.get("play_by_play_v2", {})
    pbp_v3 = raw.get("play_by_play_v3", {})

    game_summary_rows = summary_v2.get("GameSummary", [])
    game_header_rows = summary_v2.get("GameHeader", [])
    line_score_rows = summary_v2.get("LineScore", [])
    officials_rows_v2 = summary_v2.get("Officials", [])

    summary3 = summary_v3.get("boxScoreSummary", {})
    officials_rows_v3 = summary3.get("officials", [])
    team_stats_rows = traditional.get("TeamStats", [])
    pbp_rows_v2 = pbp_v2.get("PlayByPlay", [])
    pbp_rows_v3 = pbp_v3.get("game", {}).get("actions", [])

    game_header = game_header_rows[0] if game_header_rows else {}
    game_summary = game_summary_rows[0] if game_summary_rows else {}

    home_team_id = game_header.get("HOME_TEAM_ID") or summary3.get("homeTeamId")
    away_team_id = game_header.get("VISITOR_TEAM_ID") or summary3.get("awayTeamId")

    home_line = _find_first(line_score_rows, "TEAM_ID", home_team_id) or {}
    away_line = _find_first(line_score_rows, "TEAM_ID", away_team_id) or {}

    if not home_line and summary3.get("homeTeam"):
        home_line = {
            "TEAM_ABBREVIATION": summary3.get("homeTeam", {}).get("teamTricode"),
        }
    if not away_line and summary3.get("awayTeam"):
        away_line = {
            "TEAM_ABBREVIATION": summary3.get("awayTeam", {}).get("teamTricode"),
        }

    normalized_officials: list[dict[str, Any]] = []
    if officials_rows_v2:
        normalized_officials = [
            {
                "official_id": row.get("OFFICIAL_ID"),
                "first_name": row.get("FIRST_NAME"),
                "last_name": row.get("LAST_NAME"),
                "jersey_num": row.get("JERSEY_NUM"),
            }
            for row in officials_rows_v2
        ]
    elif officials_rows_v3:
        normalized_officials = [
            {
                "official_id": row.get("personId"),
                "first_name": row.get("firstName"),
                "last_name": row.get("familyName"),
                "jersey_num": row.get("jerseyNum"),
            }
            for row in officials_rows_v3
        ]

    normalized_team_stats = [
        {
            "team_id": row.get("TEAM_ID"),
            "team_name": row.get("TEAM_NAME"),
            "team_abbreviation": row.get("TEAM_ABBREVIATION"),
            "min": row.get("MIN"),
            "pts": _safe_int(row.get("PTS")),
            "fta": _safe_int(row.get("FTA")),
            "ftm": _safe_int(row.get("FTM")),
            "pf": _safe_int(row.get("PF")),
            "oreb": _safe_int(row.get("OREB")),
            "dreb": _safe_int(row.get("DREB")),
            "reb": _safe_int(row.get("REB")),
            "ast": _safe_int(row.get("AST")),
            "tov": _safe_int(row.get("TO")),
            "stl": _safe_int(row.get("STL")),
            "blk": _safe_int(row.get("BLK")),
            "plus_minus": _safe_int(row.get("PLUS_MINUS")),
        }
        for row in team_stats_rows
    ]

    normalized_pbp: list[dict[str, Any]] = []
    if pbp_rows_v2:
        normalized_pbp = [
            {
                "event_num": row.get("EVENTNUM"),
                "event_msg_type": row.get("EVENTMSGTYPE"),
                "event_msg_action_type": row.get("EVENTMSGACTIONTYPE"),
                "period": row.get("PERIOD"),
                "pctimestring": row.get("PCTIMESTRING"),
                "homedescription": row.get("HOMEDESCRIPTION"),
                "visitordescription": row.get("VISITORDESCRIPTION"),
                "neutraldescription": row.get("NEUTRALDESCRIPTION"),
                "score": row.get("SCORE"),
                "scoremargin": row.get("SCOREMARGIN"),
                "player1_id": row.get("PLAYER1_ID"),
                "player1_team_id": row.get("PLAYER1_TEAM_ID"),
                "player2_id": row.get("PLAYER2_ID"),
                "player2_team_id": row.get("PLAYER2_TEAM_ID"),
            }
            for row in pbp_rows_v2
        ]
    elif pbp_rows_v3:
        normalized_pbp = [
            {
                "event_num": row.get("actionNumber"),
                "event_msg_type": row.get("actionType"),
                "event_msg_action_type": row.get("subType"),
                "period": row.get("period"),
                "pctimestring": row.get("clock"),
                "homedescription": None,
                "visitordescription": None,
                "neutraldescription": row.get("description"),
                "score": (
                    f"{row.get('scoreAway')}-{row.get('scoreHome')}"
                    if row.get("scoreAway") is not None and row.get("scoreHome") is not None
                    else None
                ),
                "scoremargin": None,
                "player1_id": row.get("personId"),
                "player1_team_id": row.get("teamId"),
                "player2_id": None,
                "player2_team_id": None,
            }
            for row in pbp_rows_v3
        ]

    return {
        "ingestion": {
            "game_id": raw.get("game_id"),
            "fetched_at_utc": raw.get("fetched_at_utc"),
            "source": "nba_api",
        },
        "game": {
            "game_id": raw.get("game_id"),
            "game_date_est": game_header.get("GAME_DATE_EST") or summary3.get("gameEt"),
            "season": game_header.get("SEASON"),
            "game_status_id": game_header.get("GAME_STATUS_ID") or summary3.get("gameStatus"),
            "game_status_text": game_header.get("GAME_STATUS_TEXT") or summary3.get("gameStatusText"),
            "arena": game_summary.get("ARENA") or summary3.get("arena", {}).get("arenaName"),
            "attendance": game_summary.get("ATTENDANCE") or summary3.get("attendance"),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_team_abbreviation": home_line.get("TEAM_ABBREVIATION"),
            "away_team_abbreviation": away_line.get("TEAM_ABBREVIATION"),
            "home_score": _safe_int(game_header.get("PTS_HOME") or summary3.get("homeTeam", {}).get("score")),
            "away_score": _safe_int(game_header.get("PTS_VISITOR") or summary3.get("awayTeam", {}).get("score")),
        },
        "officials": normalized_officials,
        "team_stats": normalized_team_stats,
        "play_by_play": normalized_pbp,
        "counts": {
            "officials": len(normalized_officials),
            "team_stats_rows": len(normalized_team_stats),
            "play_by_play_rows": len(normalized_pbp),
        },
    }
