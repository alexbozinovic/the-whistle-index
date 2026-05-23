import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FilteredDataService } from '../../core/filtered-data.service';

@Component({
  selector: 'app-teams-page',
  standalone: true,
  imports: [AsyncPipe, DatePipe, DecimalPipe, RouterLink],
  templateUrl: './teams-page.html',
  styleUrl: './teams-page.scss',
})
export class TeamsPageComponent {
  private readonly filtered = inject(FilteredDataService);
  readonly teams$ = this.filtered.getFilteredTeams();
  readonly range$ = this.filtered.range$;
}
