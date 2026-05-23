import { Component, inject } from '@angular/core';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FilteredDataService } from '../../core/filtered-data.service';

@Component({
  selector: 'app-leaderboard-page',
  standalone: true,
  imports: [AsyncPipe, RouterLink, DecimalPipe],
  templateUrl: './leaderboard-page.html',
  styleUrl: './leaderboard-page.scss',
})
export class LeaderboardPageComponent {
  private readonly filtered = inject(FilteredDataService);

  readonly leaderboard$ = this.filtered.getFilteredLeaderboard();
  readonly games$ = this.filtered.getFilteredGames();
  readonly range$ = this.filtered.range$;
}
