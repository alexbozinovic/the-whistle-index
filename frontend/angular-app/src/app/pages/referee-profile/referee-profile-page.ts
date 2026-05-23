import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { combineLatest, map } from 'rxjs';
import { SnapshotDataService } from '../../core/snapshot-data.service';

@Component({
  selector: 'app-referee-profile-page',
  standalone: true,
  imports: [AsyncPipe, DatePipe, DecimalPipe, RouterLink],
  templateUrl: './referee-profile-page.html',
  styleUrl: './referee-profile-page.scss',
})
export class RefereeProfilePageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly data = inject(SnapshotDataService);

  readonly referee$ = combineLatest([
    this.route.paramMap.pipe(map((params) => Number(params.get('refereeId') ?? 0))),
    this.data.getReferees(),
  ]).pipe(map(([id, refs]) => refs.find((ref) => ref.referee_id === id)));
}
