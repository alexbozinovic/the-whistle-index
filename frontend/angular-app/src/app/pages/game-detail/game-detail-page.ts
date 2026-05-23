import { Component, inject } from '@angular/core';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { combineLatest, map } from 'rxjs';
import { SnapshotDataService } from '../../core/snapshot-data.service';

@Component({
  selector: 'app-game-detail-page',
  standalone: true,
  imports: [AsyncPipe, DecimalPipe, RouterLink],
  templateUrl: './game-detail-page.html',
  styleUrl: './game-detail-page.scss',
})
export class GameDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly data = inject(SnapshotDataService);

  readonly game$ = combineLatest([
    this.route.paramMap.pipe(map((params) => params.get('gameId') ?? '')),
    this.data.getGames(),
  ]).pipe(map(([gameId, games]) => games.find((g) => g.game_id === gameId)));
}
