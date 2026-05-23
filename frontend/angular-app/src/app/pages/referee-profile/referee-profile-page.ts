import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe, DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { switchMap, map } from 'rxjs';
import { FilteredDataService } from '../../core/filtered-data.service';

@Component({
  selector: 'app-referee-profile-page',
  standalone: true,
  imports: [AsyncPipe, DatePipe, DecimalPipe, RouterLink],
  templateUrl: './referee-profile-page.html',
  styleUrl: './referee-profile-page.scss',
})
export class RefereeProfilePageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly filtered = inject(FilteredDataService);

  readonly range$ = this.filtered.range$;

  /** Re-derives when the route changes OR when the date range changes. */
  readonly profile$ = this.route.paramMap.pipe(
    switchMap((params) => this.filtered.getFilteredReferee(Number(params.get('refereeId') ?? 0))),
  );
}
