"""
L2M (Last Two Minute Report) parser.

Reads the cached 2023-24 CSV and the BoxScoreTraditionalV2 player roster
for a given game to produce a structured L2M artifact at:
    artifacts/l2m/{game_id}.json

Decision codes used in the CSV:
    CC   – Correct Call
    CNC  – Correct Non-Call
    INC  – Incorrect Non-Call  (foul MISSED — disadvantaged team harmed)
    IC   – Incorrect Call      (phantom foul — committing player's team harmed)
    NA   – Not Applicable (no assessment)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from nba_api.stats.endpoints import BoxScoreTraditionalV2

# Decisions that represent officiating errors
INCORRECT_DECISIONS: frozenset[str] = frozenset({"INC", "IC"})


def _player_team_map(game_id: str, timeout: int = 30) -> dict[str, str]:
    """
    Return {player_full_name_lower: team_abbreviation} for all players in the game.
    Falls back to empty dict on any API error.
    """
    try:
        d = BoxScoreTraditionalV2(game_id=game_id, timeout=timeout).get_normalized_dict()
        mapping: dict[str, str] = {}
        for row in d.get("PlayerStats", []):
            first = str(row.get("PLAYER_NAME") or "").strip()
            abbr = str(row.get("TEAM_ABBREVIATION") or "").strip()
            if first and abbr:
                mapping[first.lower()] = abbr
        return mapping
    except Exception:
        return {}


def _resolve_team(player_name: str, player_map: dict[str, str]) -> str | None:
    """Fuzzy-match a player name from the L2M CSV to a team abbreviation."""
    if not player_name:
        return None
    key = player_name.strip().lower()
    if key in player_map:
        return player_map[key]
    # Try last-name-only match as fallback
    last = key.split()[-1] if key.split() else ""
    for full_name, abbr in player_map.items():
        if last and full_name.endswith(last):
            return abbr
    return None


def parse_l2m(
    game_id: str,
    *,
    csv_path: Path,
    home_team_abbreviation: str,
    away_team_abbreviation: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Parse L2M rows for *game_id* and return a structured summary dict.

    Keys in returned dict:
      game_id, home_team_abbreviation, away_team_abbreviation,
      total_events, incorrect_events (list of dicts),
      home_net_benefit, away_net_benefit,
      home_incorrect_favored, away_incorrect_favored
    """
    player_map = _player_team_map(game_id, timeout=timeout)

    all_events: list[dict[str, Any]] = []
    incorrect_events: list[dict[str, Any]] = []

    with csv_path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("game_id", "").replace("gameId=", "").strip() != game_id:
                continue

            decision = (row.get("decision") or "").strip().upper()
            call_type = (row.get("call_type") or "").strip()
            committing = (row.get("committing") or "").strip()
            disadvantaged = (row.get("disadvantaged") or "").strip()
            period = (row.get("period") or "").strip()
            game_time = (row.get("time") or "").strip()
            comments = (row.get("comments") or "").strip()

            event: dict[str, Any] = {
                "period": period,
                "time": game_time,
                "call_type": call_type,
                "committing_player": committing,
                "disadvantaged_player": disadvantaged,
                "decision": decision,
                "comments": comments,
            }
            all_events.append(event)

            if decision not in INCORRECT_DECISIONS:
                continue

            # Determine which team was harmed and which benefited.
            #
            # INC (Incorrect Non-Call): foul was missed.
            #   - committing player's team fouled and got away with it → they BENEFIT
            #   - disadvantaged player's team was fouled and got no call → they LOSE
            # IC (Incorrect Call): phantom foul called.
            #   - committing player's team was penalized for nothing → they LOSE
            #   - disadvantaged player's team gained free throws they didn't earn → they BENEFIT

            disadv_team = _resolve_team(disadvantaged, player_map)
            commit_team = _resolve_team(committing, player_map)

            if decision == "INC":
                # Missed call: committing team benefited
                benefiting_team = commit_team
                harmed_team = disadv_team
            else:
                # IC: phantom call: disadvantaged team benefited
                benefiting_team = disadv_team
                harmed_team = commit_team

            event["committing_team"] = commit_team
            event["disadvantaged_team"] = disadv_team
            event["benefiting_team"] = benefiting_team
            event["harmed_team"] = harmed_team
            incorrect_events.append(event)

    # Tally net benefit per team (number of incorrect events that benefited each side)
    home_favored = sum(
        1 for e in incorrect_events
        if e.get("benefiting_team") == home_team_abbreviation
    )
    away_favored = sum(
        1 for e in incorrect_events
        if e.get("benefiting_team") == away_team_abbreviation
    )
    unresolved = len(incorrect_events) - home_favored - away_favored

    return {
        "game_id": game_id,
        "home_team_abbreviation": home_team_abbreviation,
        "away_team_abbreviation": away_team_abbreviation,
        "total_events": len(all_events),
        "incorrect_count": len(incorrect_events),
        "home_l2m_benefit": home_favored,
        "away_l2m_benefit": away_favored,
        "l2m_net_home": home_favored - away_favored,
        "unresolved_count": unresolved,
        "incorrect_events": incorrect_events,
    }
