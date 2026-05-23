import { Component } from '@angular/core';

@Component({
  selector: 'app-methodology-page',
  standalone: true,
  templateUrl: './methodology-page.html',
  styleUrl: './methodology-page.scss'
})
export class MethodologyPageComponent {
  readonly metricCards = [
    {
      title: 'Referee Impact Score',
      body: 'How much an officiating crew appears to shape the measurable flow of a game.'
    },
    {
      title: 'Home Whistle Score',
      body: 'Whether game whistle patterns lean toward home-side advantage in fouls and free throws.'
    },
    {
      title: 'Game Control Score',
      body: 'How whistle-heavy and intervention-heavy the environment was overall.'
    },
    {
      title: 'Clutch Influence Score',
      body: 'How active and asymmetric whistle patterns were in close late-game moments.'
    }
  ];

  readonly limitations = [
    'Current model version is an equal-weight baseline (mvp_equal_weights_v0).',
    'Box score and play-by-play feeds can differ slightly due to event labeling.',
    'No intent inference is performed, and no corruption claim is made.',
    'Context adjustments (pace, style, usage, game state) are planned, not complete.'
  ];

  readonly dataSources = [
    'NBA game metadata, box scores, and play-by-play via nba_api.',
    'Referee crew assignments where available in NBA endpoint payloads.',
    'Derived team and referee metrics from project-owned Python scoring scripts.',
    'Last Two Minute Reports and betting datasets are planned future inputs.'
  ];
}
