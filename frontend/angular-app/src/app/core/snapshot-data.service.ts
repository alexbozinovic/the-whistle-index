import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, shareReplay } from 'rxjs';
import {
  GameSummary,
  LeaderboardRow,
  RefProfile,
  SnapshotData,
  TeamProfile,
} from './snapshot.types';

@Injectable({
  providedIn: 'root',
})
export class SnapshotDataService {
  private readonly http = inject(HttpClient);

  private readonly snapshot$: Observable<SnapshotData> = this.http
    .get<SnapshotData>('/data/snapshot.json')
    .pipe(shareReplay(1));

  getSnapshot(): Observable<SnapshotData> {
    return this.snapshot$;
  }

  getLeaderboard(): Observable<LeaderboardRow[]> {
    return this.snapshot$.pipe(map((data) => data.leaderboard));
  }

  getGames(): Observable<GameSummary[]> {
    return this.snapshot$.pipe(map((data) => data.games));
  }

  getGame(gameId: string): Observable<GameSummary | undefined> {
    return this.getGames().pipe(
      map((games) => games.find((game) => game.game_id === gameId))
    );
  }

  getReferees(): Observable<RefProfile[]> {
    return this.snapshot$.pipe(map((data) => data.referees));
  }

  getReferee(refereeId: number): Observable<RefProfile | undefined> {
    return this.getReferees().pipe(
      map((rows) => rows.find((row) => row.referee_id === refereeId))
    );
  }

  getTeams(): Observable<TeamProfile[]> {
    return this.snapshot$.pipe(map((data) => data.teams ?? []));
  }

  getTeam(abbr: string): Observable<TeamProfile | undefined> {
    return this.getTeams().pipe(
      map((rows) => rows.find((t) => t.team_abbreviation === abbr))
    );
  }
}
