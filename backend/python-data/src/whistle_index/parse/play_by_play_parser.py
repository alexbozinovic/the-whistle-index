from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _to_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_clock_seconds_remaining(clock_value: str | None) -> int | None:
    if not clock_value:
        return None

    # V3 clock format: PT10M35.00S
    if clock_value.startswith("PT") and "M" in clock_value and "S" in clock_value:
        try:
            minutes_part = clock_value.split("PT", maxsplit=1)[1].split("M", maxsplit=1)[0]
            seconds_part = clock_value.split("M", maxsplit=1)[1].replace("S", "")
            minutes = int(minutes_part)
            seconds = float(seconds_part)
            return int(minutes * 60 + seconds)
        except (ValueError, IndexError):
            return None

    # V2 fallback format: MM:SS
    if ":" in clock_value:
        try:
            minutes_part, seconds_part = clock_value.split(":", maxsplit=1)
            return int(minutes_part) * 60 + int(seconds_part)
        except ValueError:
            return None

    return None


def _parse_score(score: str | None) -> tuple[int | None, int | None]:
    if not score or "-" not in score:
        return (None, None)

    left, right = score.split("-", maxsplit=1)
    away_score = _to_int(left.strip())
    home_score = _to_int(right.strip())
    return (away_score, home_score)


@dataclass
class TeamWhistleCounts:
    fouls_called: int = 0
    free_throw_attempts: int = 0
    fourth_quarter_fouls_called: int = 0
    fourth_quarter_free_throw_attempts: int = 0
    clutch_fouls_called: int = 0
    clutch_free_throw_attempts: int = 0


def extract_whistle_features(normalized: dict[str, Any]) -> dict[str, Any]:
    game = normalized.get("game", {})
    plays = normalized.get("play_by_play", [])
    team_rows = normalized.get("team_stats", [])

    home_team_id = _to_int(game.get("home_team_id"))
    away_team_id = _to_int(game.get("away_team_id"))

    team_map: dict[int, TeamWhistleCounts] = {}
    for row in team_rows:
        team_id = _to_int(row.get("team_id"))
        if team_id is not None:
            team_map[team_id] = TeamWhistleCounts()

    if home_team_id is not None and home_team_id not in team_map:
        team_map[home_team_id] = TeamWhistleCounts()
    if away_team_id is not None and away_team_id not in team_map:
        team_map[away_team_id] = TeamWhistleCounts()

    parsed_events: list[dict[str, Any]] = []
    current_away_score: int | None = None
    current_home_score: int | None = None

    for row in plays:
        event_type = str(row.get("event_msg_type") or "")
        event_action_type = str(row.get("event_msg_action_type") or "")
        description = str(row.get("neutraldescription") or "")
        event_type_lower = event_type.lower()
        description_lower = description.lower()

        is_foul = "foul" in event_type_lower or "foul" in description_lower
        is_free_throw = "free throw" in event_type_lower or "free throw" in description_lower

        if not is_foul and not is_free_throw:
            continue

        team_id = _to_int(row.get("player1_team_id"))
        if team_id is None or team_id == 0:
            continue
        if team_id not in team_map:
            team_map[team_id] = TeamWhistleCounts()

        period = _to_int(row.get("period"))
        clock_raw = row.get("pctimestring")
        seconds_remaining = _parse_clock_seconds_remaining(str(clock_raw) if clock_raw else None)

        row_away_score, row_home_score = _parse_score(row.get("score"))
        if row_away_score is not None and row_home_score is not None:
            current_away_score = row_away_score
            current_home_score = row_home_score

        away_score = current_away_score
        home_score = current_home_score
        score_margin_abs = None
        if away_score is not None and home_score is not None:
            score_margin_abs = abs(away_score - home_score)

        is_fourth_quarter = period == 4
        is_clutch = bool(
            period is not None
            and period >= 4
            and seconds_remaining is not None
            and seconds_remaining <= 300
            and score_margin_abs is not None
            and score_margin_abs <= 5
        )

        counts = team_map[team_id]
        if is_foul:
            counts.fouls_called += 1
            if is_fourth_quarter:
                counts.fourth_quarter_fouls_called += 1
            if is_clutch:
                counts.clutch_fouls_called += 1

        if is_free_throw:
            counts.free_throw_attempts += 1
            if is_fourth_quarter:
                counts.fourth_quarter_free_throw_attempts += 1
            if is_clutch:
                counts.clutch_free_throw_attempts += 1

        parsed_events.append(
            {
                "event_num": row.get("event_num"),
                "team_id": team_id,
                "event_kind": "foul" if is_foul and not is_free_throw else "free_throw" if is_free_throw and not is_foul else "mixed",
                "event_msg_type": event_type,
                "event_msg_action_type": event_action_type,
                "description": description,
                "period": period,
                "clock": clock_raw,
                "seconds_remaining_in_period": seconds_remaining,
                "is_fourth_quarter": is_fourth_quarter,
                "is_clutch": is_clutch,
                "away_score": away_score,
                "home_score": home_score,
                "score_margin_abs": score_margin_abs,
            }
        )

    def _counts_for(team_id: int | None) -> TeamWhistleCounts:
        if team_id is None:
            return TeamWhistleCounts()
        return team_map.get(team_id, TeamWhistleCounts())

    home = _counts_for(home_team_id)
    away = _counts_for(away_team_id)

    team_breakdown: list[dict[str, Any]] = []
    for row in team_rows:
        team_id = _to_int(row.get("team_id"))
        if team_id is None:
            continue
        c = team_map.get(team_id, TeamWhistleCounts())
        team_breakdown.append(
            {
                "team_id": team_id,
                "team_abbreviation": row.get("team_abbreviation"),
                "parsed_fouls_called": c.fouls_called,
                "parsed_free_throw_attempts": c.free_throw_attempts,
                "parsed_fourth_quarter_fouls_called": c.fourth_quarter_fouls_called,
                "parsed_fourth_quarter_free_throw_attempts": c.fourth_quarter_free_throw_attempts,
                "parsed_clutch_fouls_called": c.clutch_fouls_called,
                "parsed_clutch_free_throw_attempts": c.clutch_free_throw_attempts,
                "boxscore_pf": _to_int(row.get("pf")),
                "boxscore_fta": _to_int(row.get("fta")),
            }
        )

    return {
        "game_id": game.get("game_id"),
        "clutch_definition": {
            "period": "4th or overtime",
            "time_remaining_seconds_max": 300,
            "score_margin_abs_max": 5,
        },
        "parsed_event_counts": {
            "total_whistle_events": len(parsed_events),
            "foul_events": sum(1 for e in parsed_events if e["event_kind"] in {"foul", "mixed"}),
            "free_throw_events": sum(1 for e in parsed_events if e["event_kind"] in {"free_throw", "mixed"}),
            "clutch_whistle_events": sum(1 for e in parsed_events if e["is_clutch"]),
        },
        "differential_primitives": {
            "home_minus_away_fouls_called": home.fouls_called - away.fouls_called,
            "home_minus_away_free_throw_attempts": home.free_throw_attempts - away.free_throw_attempts,
            "home_minus_away_fourth_quarter_fouls_called": home.fourth_quarter_fouls_called - away.fourth_quarter_fouls_called,
            "home_minus_away_fourth_quarter_free_throw_attempts": home.fourth_quarter_free_throw_attempts - away.fourth_quarter_free_throw_attempts,
            "home_minus_away_clutch_fouls_called": home.clutch_fouls_called - away.clutch_fouls_called,
            "home_minus_away_clutch_free_throw_attempts": home.clutch_free_throw_attempts - away.clutch_free_throw_attempts,
        },
        "team_breakdown": team_breakdown,
        "whistle_events": parsed_events,
    }
