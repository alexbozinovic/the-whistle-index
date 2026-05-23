import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { DateRangePickerComponent } from './shared/date-range-picker/date-range-picker';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, DateRangePickerComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
