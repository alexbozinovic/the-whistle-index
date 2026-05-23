import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type DateRangePreset = 'season' | 'last30' | 'last7' | 'all' | 'custom';

export interface DateRange {
  start: Date;
  end: Date;
  preset: DateRangePreset;
}

/** Returns Oct 1 of the most-recently-started NBA season. */
function currentSeasonStart(): Date {
  const now = new Date();
  const year = now.getMonth() < 6 ? now.getFullYear() - 1 : now.getFullYear();
  return new Date(year, 9, 1);
}

@Injectable({ providedIn: 'root' })
export class DateRangeService {
  private readonly _range$ = new BehaviorSubject<DateRange>({
    start: new Date(2000, 0, 1),
    end: new Date(),
    preset: 'all',
  });

  readonly range$ = this._range$.asObservable();

  get current(): DateRange {
    return this._range$.value;
  }

  setRange(start: Date, end: Date): void {
    this._range$.next({ start, end, preset: 'custom' });
  }

  setPreset(preset: Exclude<DateRangePreset, 'custom'>): void {
    const now = new Date();
    let start: Date;
    switch (preset) {
      case 'season': start = currentSeasonStart(); break;
      case 'last30': start = new Date(now); start.setDate(start.getDate() - 30); break;
      case 'last7':  start = new Date(now); start.setDate(start.getDate() - 7);  break;
      case 'all':    start = new Date(2000, 0, 1); break;
    }
    this._range$.next({ start, end: now, preset });
  }
}
