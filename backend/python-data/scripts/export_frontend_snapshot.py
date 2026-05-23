from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return round(variance ** 0.5, 2)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ref_name(ref: dict[str, Any]) -> str:
    first = str(ref.get("first_name") or "").strip()
    last = str(ref.get("last_name") or "").strip()
    return f"{first} {last}".strip() or "Unknown"


def _load_enrichment(data_dir: Path) -> dict[str, dict[str, Any]]:
    path = data_dir / "referee_enrichment.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_snapshot(artifacts_dir: Path, data_dir: Path | None = None) -> dict[str, Any]:
    raw_dir = artifacts_dir / "raw"
    parsed_dir = artifacts_dir / "parsed"
    scored_dir = artifacts_dir / "scored"

    enrichment = _load_enrichment(data_dir) if data_dir else {}

    game_ids = sorted(
        p.stem for p in scored_dir.glob("*.json") if (raw_dir / f"{p.stem}.json").exists()
    )

    games: list[dict[str, Any]] = []
    ref_rows: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for game_id in game_ids:
        raw = _load_json(raw_dir / f"{game_id}.json")
        parsed = _load_json(parsed_dir / f"{game_id}.json") if (parsed_dir / f"{game_id}.json").exists() else {}
        scored = _load_json(scored_dir / f"{game_id}.json")

        game = raw.get("game", {})
        score = scored.get("scores", {})
        lean = scored.get("team_whistle_lean", {})

        game_item = {
            "game_id": game_id,
            "game_date_est": game.get("game_date_est"),
            "home_team_id": game.get("home_team_id"),
            "away_team_id": game.get("away_team_id"),
            "home_team_abbreviation": game.get("home_team_abbreviation"),
            "away_team_abbreviation": game.get("away_team_abbreviation"),
            "home_score": game.get("home_score"),
            "away_score": game.get("away_score"),
            "crew": scored.get("crew", []),
            "scores": score,
            "team_whistle_lean": lean,
            "differential_primitives": parsed.get("differential_primitives", {}),
            "main_drivers": scored.get("main_drivers", []),
        }
        games.append(game_item)

        for ref in scored.get("crew", []):
            ref_id = ref.get("official_id")
            if ref_id is None:
                continue
            ref_rows[int(ref_id)].append(
                {
                    "game_id": game_id,
                    "game_date_est": game.get("game_date_est"),
                    "impact_score": score.get("crew_impact_score"),
                    "home_whistle_score": score.get("home_whistle_score"),
                    "game_control_score": score.get("game_control_score"),
                    "clutch_influence_score": score.get("clutch_influence_score"),
                    "team_whistle_lean": lean,
                    "main_drivers": scored.get("main_drivers", []),
                    "ref": ref,
                }
            )

    leaderboard: list[dict[str, Any]] = []
    referees: list[dict[str, Any]] = []

    for ref_id, rows in ref_rows.items():
        rows_sorted = sorted(rows, key=lambda r: str(r.get("game_date_est") or ""), reverse=True)
        n = len(rows)

        def _metric(key: str) -> list[float]:
            return [float(r.get(key) or 0) for r in rows]

        impact_values = _metric("impact_score")
        home_whistle_values = _metric("home_whistle_score")
        game_control_values = _metric("game_control_score")
        clutch_values = _metric("clutch_influence_score")

        lean_values = [
            abs(float((r.get("team_whistle_lean") or {}).get("home_team_lean_points") or 0))
            for r in rows
        ]

        favored_side_counts = {"home": 0, "away": 0, "even": 0}
        favored_team_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            lean = row.get("team_whistle_lean") or {}
            favored_team = str(lean.get("favored_team_abbreviation") or "EVEN")
            favored_team_counts[favored_team] += 1
            home_lean = float(lean.get("home_team_lean_points") or 0)
            if home_lean > 0:
                favored_side_counts["home"] += 1
            elif home_lean < 0:
                favored_side_counts["away"] += 1
            else:
                favored_side_counts["even"] += 1

        latest3 = impact_values[:3]
        prev3 = impact_values[3:6]
        trend_delta = round(_avg(latest3) - _avg(prev3), 2) if prev3 else 0.0

        favored_team_rank = sorted(
            favored_team_counts.items(), key=lambda item: item[1], reverse=True
        )[:3]

        ref_meta = rows_sorted[0].get("ref", {})
        enriched = enrichment.get(str(ref_id), {})
        item = {
            "referee_id": ref_id,
            "name": _ref_name(ref_meta),
            "jersey_num": str(ref_meta.get("jersey_num") or "").strip() or None,
            "headshot_url": enriched.get("headshot_url"),
            "hometown": enriched.get("hometown"),
            "years_experience": enriched.get("years_experience"),
            "nba_debut_year": enriched.get("nba_debut_year"),
            "games_worked": n,
            "impact_score": _avg(impact_values),
            "home_whistle_score": _avg(home_whistle_values),
            "game_control_score": _avg(game_control_values),
            "clutch_influence_score": _avg(clutch_values),
            "impact_volatility": _stddev(impact_values),
            "avg_abs_team_lean": _avg(lean_values),
            "recent_trend_delta": trend_delta,
            "favored_side_share": {
                "home": round(favored_side_counts["home"] / n, 3) if n else 0.0,
                "away": round(favored_side_counts["away"] / n, 3) if n else 0.0,
                "even": round(favored_side_counts["even"] / n, 3) if n else 0.0,
            },
        }
        leaderboard.append(item)
        referees.append(
            {
                **item,
                "recent_games": rows_sorted[:10],
                "impact_trend": [
                    {
                        "game_id": row.get("game_id"),
                        "game_date_est": row.get("game_date_est"),
                        "impact_score": row.get("impact_score"),
                    }
                    for row in rows_sorted[:10]
                ],
                "favored_team_rank": [
                    {
                        "team": team,
                        "count": count,
                    }
                    for team, count in favored_team_rank
                ],
            }
        )

    leaderboard.sort(key=lambda r: (r["impact_score"], r["games_worked"]), reverse=True)
    referees.sort(key=lambda r: r["name"])
    games.sort(key=lambda g: str(g.get("game_date_est") or ""), reverse=True)

    teams = _build_teams(games)

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "games": games,
        "leaderboard": leaderboard,
        "referees": referees,
        "teams": teams,
    }


def _build_teams(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate per-team whistle stats from the already-built games list."""
    team_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for g in games:
        lean = g.get("team_whistle_lean") or {}
        home_lean_pts = float(lean.get("home_team_lean_points") or 0)
        away_lean_pts = float(lean.get("away_team_lean_points") or 0)
        crew_abbrs = [
            f"{r.get('first_name', '')} {r.get('last_name', '')}".strip()
            for r in g.get("crew", [])
        ]
        crew_ids = [r.get("official_id") for r in g.get("crew", []) if r.get("official_id")]

        base = {
            "game_id": g["game_id"],
            "game_date_est": g.get("game_date_est"),
            "home_score": g.get("home_score"),
            "away_score": g.get("away_score"),
            "home_team_abbreviation": g.get("home_team_abbreviation"),
            "away_team_abbreviation": g.get("away_team_abbreviation"),
            "crew_abbrs": crew_abbrs,
            "crew_ids": crew_ids,
        }

        home_abbr = g.get("home_team_abbreviation") or ""
        away_abbr = g.get("away_team_abbreviation") or ""

        if home_abbr:
            team_rows[home_abbr].append(
                {
                    **base,
                    "is_home": True,
                    "team_lean_points": home_lean_pts,
                    "opponent_abbreviation": away_abbr,
                    "team_score": g.get("home_score"),
                    "opponent_score": g.get("away_score"),
                }
            )
        if away_abbr:
            team_rows[away_abbr].append(
                {
                    **base,
                    "is_home": False,
                    "team_lean_points": away_lean_pts,
                    "opponent_abbreviation": home_abbr,
                    "team_score": g.get("away_score"),
                    "opponent_score": g.get("home_score"),
                }
            )

    teams: list[dict[str, Any]] = []

    for abbr, rows in team_rows.items():
        rows_sorted = sorted(rows, key=lambda r: str(r.get("game_date_est") or ""), reverse=True)
        n = len(rows)
        lean_pts = [r["team_lean_points"] for r in rows]
        home_rows = [r for r in rows if r["is_home"]]
        away_rows = [r for r in rows if not r["is_home"]]

        # Per-referee lean for this team
        ref_lean: dict[int, list[float]] = defaultdict(list)
        for row in rows:
            for rid in row["crew_ids"]:
                ref_lean[int(rid)].append(row["team_lean_points"])

        ref_avg = {rid: _avg(vals) for rid, vals in ref_lean.items()}
        sorted_refs = sorted(ref_avg.items(), key=lambda x: x[1], reverse=True)
        most_favorable_refs = [{"referee_id": rid, "avg_lean": v} for rid, v in sorted_refs[:3]]
        least_favorable_refs = [{"referee_id": rid, "avg_lean": v} for rid, v in sorted_refs[-3:]]

        teams.append(
            {
                "team_abbreviation": abbr,
                "games_played": n,
                "avg_whistle_lean": _avg(lean_pts),
                "home_avg_lean": _avg([r["team_lean_points"] for r in home_rows]),
                "away_avg_lean": _avg([r["team_lean_points"] for r in away_rows]),
                "home_games": len(home_rows),
                "away_games": len(away_rows),
                "most_favorable_refs": most_favorable_refs,
                "least_favorable_refs": least_favorable_refs,
                "recent_games": rows_sorted[:10],
            }
        )

    teams.sort(key=lambda t: t["avg_whistle_lean"], reverse=True)
    return teams


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    data_dir = root / "data"
    target = (
        root.parent.parent
        / "frontend"
        / "angular-app"
        / "public"
        / "data"
        / "snapshot.json"
    )

    snapshot = build_snapshot(artifacts, data_dir=data_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Wrote frontend snapshot: {target}")
    print(
        f"games={len(snapshot['games'])}, leaderboard_rows={len(snapshot['leaderboard'])}, referees={len(snapshot['referees'])}"
    )


if __name__ == "__main__":
    main()
