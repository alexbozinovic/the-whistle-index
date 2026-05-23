import { Routes } from '@angular/router';
import { GameDetailPageComponent } from './pages/game-detail/game-detail-page';
import { LeaderboardPageComponent } from './pages/leaderboard/leaderboard-page';
import { MethodologyPageComponent } from './pages/methodology/methodology-page';
import { RefereeProfilePageComponent } from './pages/referee-profile/referee-profile-page';

export const routes: Routes = [
	{
		path: '',
		pathMatch: 'full',
		redirectTo: 'leaderboard'
	},
	{
		path: 'leaderboard',
		component: LeaderboardPageComponent
	},
	{
		path: 'games/:gameId',
		component: GameDetailPageComponent
	},
	{
		path: 'referees/:refereeId',
		component: RefereeProfilePageComponent
	},
	{
		path: 'methodology',
		component: MethodologyPageComponent
	},
	{
		path: '**',
		redirectTo: 'leaderboard'
	}
];
