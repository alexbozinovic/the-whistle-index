import { Component, inject } from '@angular/core';
import { AsyncPipe, DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { SnapshotDataService } from '../../core/snapshot-data.service';

@Component({
  selector: 'app-teams-page',
  standalone: true,
  imports: [AsyncPipe, DecimalPipe, RouterLink],
  templateUrl: './teams-page.html',
  styleUrl: './teams-page.scss',
})
export class TeamsPageComponent {
  private readonly data = inject(SnapshotDataService);
  readonly teams$ = this.data.getTeams();
}
