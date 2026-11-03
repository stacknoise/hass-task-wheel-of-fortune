/** Anwesenheit einer Person aus ihren Abwesenheitsregeln; spiegelt `domain/availability/strategies.py`. */

import type { AbsenceWire } from '../api/index.ts';
import { PREVIEW_WEEKS, WEEKDAY_COUNT } from '../constants/index.ts';
import { dayNumber, weekdayOf } from './dates.ts';

function positiveModulo(value: number, divisor: number): number {
  return ((value % divisor) + divisor) % divisor;
}

/** Ist die Person laut dieser Regel am Tag (Tageszahl) anwesend? */
function presentFor(absence: AbsenceWire, day: number): boolean {
  switch (absence.kind) {
    case 'once':
      return !(day >= dayNumber(absence.start) && day <= dayNumber(absence.end));
    case 'weekly_days':
      return !absence.weekdays.includes(weekdayOf(day));
    case 'week_rhythm': {
      const anchor = dayNumber(absence.anchor);
      const weekStart =
        anchor - positiveModulo(weekdayOf(anchor) - absence.change_weekday, WEEKDAY_COUNT);
      const index = positiveModulo(
        Math.floor((day - weekStart) / WEEKDAY_COUNT),
        absence.cycle_weeks,
      );
      return absence.present_weeks.includes(index);
    }
  }
}

/** Anwesend, wenn keine Regel Abwesenheit meldet. */
export function isPresent(absences: readonly AbsenceWire[], day: number): boolean {
  return absences.every((absence) => presentFor(absence, day));
}

/** Anwesenheit der nächsten Wochen, beginnend am Montag der Woche von `today` (`JJJJ-MM-TT`). */
export function presencePreview(
  absences: readonly AbsenceWire[],
  today: string,
  weeks: number = PREVIEW_WEEKS,
): readonly boolean[] {
  const first = dayNumber(today);
  const start = first - weekdayOf(first);
  return Array.from({ length: weeks * WEEKDAY_COUNT }, (_, offset) =>
    isPresent(absences, start + offset),
  );
}
