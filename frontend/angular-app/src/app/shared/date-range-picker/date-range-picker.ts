import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { DateRangeService, DateRangePreset } from '../../core/date-range.service';

@Component({
  selector: 'app-date-range-picker',
  standalone: true,
  imports: [AsyncPipe],
  templateUrl: './date-range-picker.html',
  styleUrl: './date-range-picker.scss',
})
export class DateRangePickerComponent {
  readonly svc = inject(DateRangeService);
  readonly range$ = this.svc.range$;

  readonly presets: { label: string; value: Exclude<DateRangePreset, 'custom'> }[] = [
    { label: 'Season',   value: 'season' },
    { label: '30 Days',  value: 'last30' },
    { label: '7 Days',   value: 'last7'  },
    { label: 'All Time', value: 'all'    },
  ];

  setPreset(preset: Exclude<DateRangePreset, 'custom'>): void {
    this.svc.setPreset(preset);
  }

  toInputValue(d: Date): string {
    return d.toISOString().slice(0, 10);
  }

  onStartChange(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    if (!val) return;
    const end = this.svc.current.end;
    this.svc.setRange(new Date(val + 'T00:00:00'), end);
  }

  onEndChange(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    if (!val) return;
    const start = this.svc.current.start;
    this.svc.setRange(start, new Date(val + 'T23:59:59'));
  }
}
