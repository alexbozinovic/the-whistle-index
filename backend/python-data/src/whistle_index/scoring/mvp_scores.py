from __future__ import annotations

from typing import Any


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _team_row(parsed: dict[str, Any], team_id: int | None) -> dict[str, Any]:
    if team_id is None:
        return {}
    for row in parsed.get("team_breakdown", []):
        if row.get("team_id") == team_id:
            return row
    return {}


def _driver_line(label: str, value: float, suffix: str = "") -> str:
    sign = "+" if value > 0 else ""
    return f"{label}: {sign}{value}{suffix}"


def compute_mvp_scores(normalized: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    game = normalized.get("game", {})
    diff = parsed.get("differential_primitives", {})

    home_team_id = game.get("home_team_id")
    away_team_id = game.get("away_team_id")
    home_team_abbreviation = game.get("home_team_abbreviation")
    away_team_abbreviation = game.get("away_team_abbreviation")

    home_row = _team_row(parsed, home_team_id)
    away_row = _team_row(parsed, away_team_id)

    diff_fouls = float(diff.get("home_minus_away_fouls_called", 0) or 0)
    diff_fta = float(diff.get("home_minus_away_free_throw_attempts", 0) or 0)
    diff_4q_fouls = float(diff.get("home_minus_away_fourth_quarter_fouls_called", 0) or 0)
    diff_4q_fta = float(diff.get("home_minus_away_fourth_quarter_free_throw_attempts", 0) or 0)
    diff_clutch_fouls = float(diff.get("home_minus_away_clutch_fouls_called", 0) or 0)
    diff_clutch_fta = float(diff.get("home_minus_away_clutch_free_throw_attempts", 0) or 0)

    # Equal-weight initial model.
    component_fta_edge = diff_fta
    component_foul_relief = -diff_fouls
    component_fourth_quarter_edge = diff_4q_fta - diff_4q_fouls
    component_clutch_edge = diff_clutch_fta - diff_clutch_fouls

    home_lean_points = round(
        (
            component_fta_edge
            + component_foul_relief
            + component_fourth_quarter_edge
            + component_clutch_edge
        )
        / 4,
        2,
    )
    away_lean_points = round(-home_lean_points, 2)

    total_fouls_called = float((home_row.get("parsed_fouls_called") or 0) + (away_row.get("parsed_fouls_called") or 0))
    total_fta = float((home_row.get("parsed_free_throw_attempts") or 0) + (away_row.get("parsed_free_throw_attempts") or 0))
    total_fourth_quarter_whistles = float(
        (home_row.get("parsed_fourth_quarter_fouls_called") or 0)
        + (away_row.get("parsed_fourth_quarter_fouls_called") or 0)
        + (home_row.get("parsed_fourth_quarter_free_throw_attempts") or 0)
        + (away_row.get("parsed_fourth_quarter_free_throw_attempts") or 0)
    )
    total_clutch_whistles = float(
        (home_row.get("parsed_clutch_fouls_called") or 0)
        + (away_row.get("parsed_clutch_fouls_called") or 0)
        + (home_row.get("parsed_clutch_free_throw_attempts") or 0)
        + (away_row.get("parsed_clutch_free_throw_attempts") or 0)
    )

    volume_score = _clamp((((total_fouls_called / 55) + (total_fta / 60)) / 2) * 100, 0, 100)
    imbalance_mean = (
        abs(component_fta_edge)
        + abs(component_foul_relief)
        + abs(component_fourth_quarter_edge)
        + abs(component_clutch_edge)
    ) / 4
    imbalance_score = _clamp((imbalance_mean / 8) * 100, 0, 100)

    crew_impact_score = round((volume_score + imbalance_score) / 2, 1)
    home_whistle_score = round(_clamp(50 + home_lean_points * 8, 0, 100), 1)
    game_control_score = round(
        _clamp(
            (total_fouls_called / 55) * 40
            + (total_fta / 60) * 40
            + (total_fourth_quarter_whistles / 30) * 20,
            0,
            100,
        ),
        1,
    )
    clutch_imbalance = abs(diff_clutch_fouls) + abs(diff_clutch_fta)
    clutch_influence_score = round(
        _clamp((total_clutch_whistles / 12) * 70 + (clutch_imbalance / 5) * 30, 0, 100),
        1,
    )

    drivers = [
        {
            "label": "Free throw edge",
            "value": component_fta_edge,
            "line": _driver_line("Home minus away free throw attempts", component_fta_edge),
        },
        {
            "label": "Foul burden relief",
            "value": component_foul_relief,
            "line": _driver_line("Away minus home fouls called", component_foul_relief),
        },
        {
            "label": "Fourth-quarter whistle edge",
            "value": component_fourth_quarter_edge,
            "line": _driver_line("4Q edge (FTA minus fouls)", component_fourth_quarter_edge),
        },
        {
            "label": "Clutch whistle edge",
            "value": component_clutch_edge,
            "line": _driver_line("Clutch edge (FTA minus fouls)", component_clutch_edge),
        },
    ]
    drivers_sorted = sorted(drivers, key=lambda item: abs(item["value"]), reverse=True)

    favored_team_id = None
    favored_team_abbreviation = "EVEN"
    if home_lean_points > 0:
        favored_team_id = home_team_id
        favored_team_abbreviation = str(home_team_abbreviation or "HOME")
    elif home_lean_points < 0:
        favored_team_id = away_team_id
        favored_team_abbreviation = str(away_team_abbreviation or "AWAY")

    return {
        "game_id": game.get("game_id"),
        "model": {
            "name": "mvp_equal_weights_v0",
            "description": "Initial equal-weight scoring model using foul and free-throw differential primitives.",
        },
        "teams": {
            "home": {
                "team_id": home_team_id,
                "abbreviation": home_team_abbreviation,
            },
            "away": {
                "team_id": away_team_id,
                "abbreviation": away_team_abbreviation,
            },
        },
        "crew": normalized.get("officials", []),
        "scores": {
            "crew_impact_score": crew_impact_score,
            "home_whistle_score": home_whistle_score,
            "game_control_score": game_control_score,
            "clutch_influence_score": clutch_influence_score,
        },
        "team_whistle_lean": {
            "home_team_lean_points": home_lean_points,
            "away_team_lean_points": away_lean_points,
            "favored_team_id": favored_team_id,
            "favored_team_abbreviation": favored_team_abbreviation,
        },
        "equal_weight_components": {
            "free_throw_edge": component_fta_edge,
            "foul_burden_relief": component_foul_relief,
            "fourth_quarter_edge": component_fourth_quarter_edge,
            "clutch_edge": component_clutch_edge,
        },
        "volume_metrics": {
            "total_fouls_called": total_fouls_called,
            "total_free_throw_attempts": total_fta,
            "total_fourth_quarter_whistles": total_fourth_quarter_whistles,
            "total_clutch_whistles": total_clutch_whistles,
            "volume_score": round(volume_score, 1),
            "imbalance_score": round(imbalance_score, 1),
        },
        "main_drivers": [driver["line"] for driver in drivers_sorted[:3]],
    }
