import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { SnapshotDataService } from '../../core/snapshot-data.service';

@Component({
  selector: 'app-leaderboard-page',
  standalone: true,
  imports: [AsyncPipe, RouterLink, DecimalPipe, DatePipe],
  templateUrl: './leaderboard-page.html',
  styleUrl: './leaderboard-page.scss',
})
export class LeaderboardPageComponent {
  private readonly data = inject(SnapshotDataService);

  readonly snapshotMeta$ = this.data
    .getSnapshot()
    .pipe(map((snapshot) => snapshot.generated_at_utc));

  readonly leaderboard$ = this.data.getLeaderboard();
  readonly games$ = this.data.getGames();
}
