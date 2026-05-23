import { Injectable, inject } from '@angular/core';
import { Observable, combineLatest, map } from 'rxjs';
import { SnapshotDataService } from './snapshot-data.service';
import { DateRangeService } from './date-range.service';
import {
  GameSummary,
  LeaderboardRow,
  RefProfile,
  RefRecentGame,
  TeamGame,
  TeamProfile,
} from './snapshot.types';

// ── Helpers ─────────────────────────────────────────────────────────────────

function _avg(vals: number[]): number {
  if (!vals.length) return 0;
  return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 10) / 10;
}

function _stddev(vals: number[]): number {
  if (vals.length < 2) return 0;
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
  const variance = vals.reduce((s, v) => s + (v - mean) ** 2, 0) / vals.length;
  return Math.round(Math.sqrt(variance) * 10) / 10;
}

function _buildLeaderboardRow(
  refId: number,
  refGames: GameSummary[],
  staticRef: RefProfile,
): LeaderboardRow {
  const sorted = [...refGames].sort((a, b) =>
    b.game_date_est.localeCompare(a.game_date_est),
  );
  const impacts = sorted.map((g) => g.scores.crew_impact_score);
  const homeWhistles = sorted.map((g) => g.scores.home_whistle_score);
  const controls = sorted.map((g) => g.scores.game_control_score);
  const clutches = sorted.map((g) => g.scores.clutch_influence_score);
  const leans = sorted.map((g) => Math.abs(g.team_whistle_lean.home_team_lean_points));

  const favSide = { home: 0, away: 0, even: 0 };
  for (const g of refGames) {
    const lean = g.team_whistle_lean.home_team_lean_points;
    if (lean > 0) favSide.home++;
    else if (lean < 0) favSide.away++;
    else favSide.even++;
  }
  const n = refGames.length;
  const latest3 = impacts.slice(0, 3);
  const prev3 = impacts.slice(3, 6);
  const trendDelta = prev3.length ? Math.round((_avg(latest3) - _avg(prev3)) * 10) / 10 : 0;

  const l2mGames = refGames.filter((g) => g.l2m_summary);
  const l2mTotal = l2mGames.reduce((s, g) => s + (g.l2m_summary?.incorrect_count ?? 0), 0);

  return {
    referee_id: refId,
    name: staticRef.name,
    jersey_num: staticRef.jersey_num,
    headshot_url: staticRef.headshot_url,
    hometown: staticRef.hometown,
    years_experience: staticRef.years_experience,
    nba_debut_year: staticRef.nba_debut_year,
    games_worked: n,
    impact_score: _avg(impacts),
    home_whistle_score: _avg(homeWhistles),
    game_control_score: _avg(controls),
    clutch_influence_score: _avg(clutches),
    impact_volatility: _stddev(impacts),
    avg_abs_team_lean: _avg(leans),
    recent_trend_delta: trendDelta,
    favored_side_share: {
      home: n ? Math.round((favSide.home / n) * 1000) / 1000 : 0,
      away: n ? Math.round((favSide.away / n) * 1000) / 1000 : 0,
      even: n ? Math.round((favSide.even / n) * 1000) / 1000 : 0,
    },
    l2m_games_worked: l2mGames.length,
    l2m_avg_incorrect_per_game: l2mGames.length ? Math.round((l2mTotal / l2mGames.length) * 100) / 100 : null,
  };
}

function _buildLeaderboard(games: GameSummary[], allRefs: RefProfile[]): LeaderboardRow[] {
  const refGamesMap = new Map<number, GameSummary[]>();
  for (const game of games) {
    for (const ref of game.crew) {
      const arr = refGamesMap.get(ref.official_id) ?? [];
      arr.push(game);
      refGamesMap.set(ref.official_id, arr);
    }
  }
  const rows: LeaderboardRow[] = [];
  for (const [refId, refGames] of refGamesMap) {
    const staticRef = allRefs.find((r) => r.referee_id === refId);
    if (!staticRef) continue;
    rows.push(_buildLeaderboardRow(refId, refGames, staticRef));
  }
  return rows.sort((a, b) => b.impact_score - a.impact_score || b.games_worked - a.games_worked);
}

function _buildTeams(games: GameSummary[]): TeamProfile[] {
  const teamMap = new Map<string, { home: GameSummary[]; away: GameSummary[] }>();
  for (const g of games) {
    const h = g.home_team_abbreviation;
    const a = g.away_team_abbreviation;
    if (h) {
      if (!teamMap.has(h)) teamMap.set(h, { home: [], away: [] });
      teamMap.get(h)!.home.push(g);
    }
    if (a) {
      if (!teamMap.has(a)) teamMap.set(a, { home: [], away: [] });
      teamMap.get(a)!.away.push(g);
    }
  }

  const teams: TeamProfile[] = [];
  for (const [abbr, { home, away }] of teamMap) {
    const allG = [...home, ...away];
    const homeLeans = home.map((g) => g.team_whistle_lean.home_team_lean_points);
    const awayLeans = away.map((g) => g.team_whistle_lean.away_team_lean_points);

    // Per-ref lean for this team
    const refLeans = new Map<number, number[]>();
    for (const g of home) {
      for (const c of g.crew) {
        const arr = refLeans.get(c.official_id) ?? [];
        arr.push(g.team_whistle_lean.home_team_lean_points);
        refLeans.set(c.official_id, arr);
      }
    }
    for (const g of away) {
      for (const c of g.crew) {
        const arr = refLeans.get(c.official_id) ?? [];
        arr.push(g.team_whistle_lean.away_team_lean_points);
        refLeans.set(c.official_id, arr);
      }
    }
    const refAvgs = Array.from(refLeans.entries())
      .map(([rid, ls]) => ({ referee_id: rid, avg_lean: _avg(ls) }))
      .sort((a, b) => b.avg_lean - a.avg_lean);

    const recentGames: TeamGame[] = allG
      .sort((a, b) => b.game_date_est.localeCompare(a.game_date_est))
      .slice(0, 10)
      .map((g) => {
        const isHome = g.home_team_abbreviation === abbr;
        return {
          game_id: g.game_id,
          game_date_est: g.game_date_est,
          is_home: isHome,
          team_score: isHome ? g.home_score : g.away_score,
          opponent_score: isHome ? g.away_score : g.home_score,
          team_lean_points: isHome
            ? g.team_whistle_lean.home_team_lean_points
            : g.team_whistle_lean.away_team_lean_points,
          opponent_abbreviation: isHome ? g.away_team_abbreviation : g.home_team_abbreviation,
          home_team_abbreviation: g.home_team_abbreviation,
          away_team_abbreviation: g.away_team_abbreviation,
        };
      });

    teams.push({
      team_abbreviation: abbr,
      games_played: allG.length,
      avg_whistle_lean: _avg([...homeLeans, ...awayLeans]),
      home_avg_lean: _avg(homeLeans),
      away_avg_lean: _avg(awayLeans),
      home_games: home.length,
      away_games: away.length,
      most_favorable_refs: refAvgs.slice(0, 3),
      least_favorable_refs: refAvgs.slice(-3).reverse(),
      recent_games: recentGames,
    });
  }
  return teams.sort((a, b) => b.avg_whistle_lean - a.avg_whistle_lean);
}

// ── Service ──────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class FilteredDataService {
  private readonly snapshot = inject(SnapshotDataService);
  private readonly dateRange = inject(DateRangeService);

  readonly range$ = this.dateRange.range$;

  getFilteredGames(): Observable<GameSummary[]> {
    return combineLatest([this.snapshot.getGames(), this.dateRange.range$]).pipe(
      map(([games, range]) =>
        games.filter((g) => {
          const d = new Date(g.game_date_est);
          return d >= range.start && d <= range.end;
        }),
      ),
    );
  }

  getFilteredLeaderboard(): Observable<LeaderboardRow[]> {
    return combineLatest([this.getFilteredGames(), this.snapshot.getReferees()]).pipe(
      map(([games, allRefs]) => _buildLeaderboard(games, allRefs)),
    );
  }

  getFilteredTeams(): Observable<TeamProfile[]> {
    return this.getFilteredGames().pipe(map((games) => _buildTeams(games)));
  }

  getFilteredTeam(abbr: string): Observable<TeamProfile | null> {
    return this.getFilteredTeams().pipe(
      map((teams) => teams.find((t) => t.team_abbreviation === abbr) ?? null),
    );
  }

  getFilteredReferee(id: number): Observable<RefProfile | null> {
    return combineLatest([this.getFilteredGames(), this.snapshot.getReferees()]).pipe(
      map(([games, allRefs]) => {
        const staticRef = allRefs.find((r) => r.referee_id === id);
        if (!staticRef) return null;

        const refGames = games.filter((g) => g.crew.some((c) => c.official_id === id));
        if (!refGames.length) {
          return {
            ...staticRef,
            games_worked: 0,
            impact_score: 0,
            home_whistle_score: 0,
            game_control_score: 0,
            clutch_influence_score: 0,
            impact_volatility: 0,
            avg_abs_team_lean: 0,
            recent_trend_delta: 0,
            favored_side_share: { home: 0, away: 0, even: 0 },
            l2m_games_worked: 0,
            l2m_avg_incorrect_per_game: null,
            recent_games: [],
            impact_trend: [],
            favored_team_rank: [],
          };
        }

        const row = _buildLeaderboardRow(id, refGames, staticRef);

        const sorted = [...refGames].sort((a, b) =>
          b.game_date_est.localeCompare(a.game_date_est),
        );
        const recentGames: RefRecentGame[] = sorted.slice(0, 10).map((g) => ({
          game_id: g.game_id,
          game_date_est: g.game_date_est,
          impact_score: g.scores.crew_impact_score,
          home_whistle_score: g.scores.home_whistle_score,
          game_control_score: g.scores.game_control_score,
          clutch_influence_score: g.scores.clutch_influence_score,
          team_whistle_lean: {
            favored_team_abbreviation: g.team_whistle_lean.favored_team_abbreviation,
          },
          main_drivers: g.main_drivers,
        }));

        const impactTrend = recentGames.map((g) => ({
          game_id: g.game_id,
          game_date_est: g.game_date_est,
          impact_score: g.impact_score,
        }));

        const teamCounts: Record<string, number> = {};
        for (const g of refGames) {
          const t = g.team_whistle_lean.favored_team_abbreviation;
          teamCounts[t] = (teamCounts[t] ?? 0) + 1;
        }
        const favored_team_rank = Object.entries(teamCounts)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([team, count]) => ({ team, count }));

        return { ...row, recent_games: recentGames, impact_trend: impactTrend, favored_team_rank };
      }),
    );
  }
}
