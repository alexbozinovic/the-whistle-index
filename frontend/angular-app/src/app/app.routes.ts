import { Routes } from '@angular/router';
import { MethodologyPageComponent } from './pages/methodology/methodology-page';

export const routes: Routes = [
	{
		path: '',
		pathMatch: 'full',
		redirectTo: 'methodology'
	},
	{
		path: 'methodology',
		component: MethodologyPageComponent
	},
	{
		path: '**',
		redirectTo: 'methodology'
	}
];
