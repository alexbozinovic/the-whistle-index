import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Observable, combineLatest, map } from 'rxjs';
import { FilteredDataService } from '../../core/filtered-data.service';
import { TeamProfile, LeaderboardRow } from '../../core/snapshot.types';

interface TeamDetailVm {
  team: TeamProfile;
  leaderboard: LeaderboardRow[];
}

@Component({
  selector: 'app-team-detail-page',
  standalone: true,
  imports: [AsyncPipe, DecimalPipe, DatePipe, RouterLink],
  templateUrl: './team-detail-page.html',
  styleUrl: './team-detail-page.scss',
})
export class TeamDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly filtered = inject(FilteredDataService);

  readonly vm$: Observable<TeamDetailVm | null> = combineLatest([
    this.route.paramMap,
    this.filtered.getFilteredTeams(),
    this.filtered.getFilteredLeaderboard(),
  ]).pipe(
    map(([params, teams, leaderboard]) => {
      const abbr = params.get('teamAbbr') ?? '';
      const team = teams.find((t) => t.team_abbreviation === abbr);
      return team ? { team, leaderboard } : null;
    })
  );

  refName(refereeId: number, leaderboard: LeaderboardRow[]): string {
    return leaderboard.find((r) => r.referee_id === refereeId)?.name ?? String(refereeId);
  }
}
