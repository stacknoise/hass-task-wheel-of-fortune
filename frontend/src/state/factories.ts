/** Fabriken der Standardwerte (Abwesenheit, Zeitplan-Eintrag, Intervall, Beginn); die Tabelle ersetzt Verzweigungen. */

import type { AbsenceWire, EntryWire, IntervalWire } from '../api/index.ts';
import {
  DEFAULT_ABSENT_WEEKDAYS,
  DEFAULT_INTERVAL_EVERY,
  DEFAULT_MIN_COUNT,
  DEFAULT_RECURRENCE_INTERVAL,
  DEFAULT_RECURRING_ABSENCE_WEEKDAYS,
  DEFAULT_RHYTHM_CHANGE_DAY,
  DEFAULT_RHYTHM_CYCLE,
  DEFAULT_START_OFFSET_HOURS,
  MS_PER_HOUR,
} from '../constants/index.ts';
import type { AbsenceKind } from '../constants/index.ts';
import { dayOf } from './dates.ts';

const FIRST_WEEK = 0;

/** Neue Abwesenheit je Art, bezogen auf den heutigen Tag (`JJJJ-MM-TT`). */
export const ABSENCE_BUILDERS: Readonly<Record<AbsenceKind, (today: string) => AbsenceWire>> = {
  once: (today) => ({ kind: 'once', start: dayOf(today), end: dayOf(today) }),
  weekly_days: () => ({ kind: 'weekly_days', weekdays: DEFAULT_ABSENT_WEEKDAYS }),
  week_rhythm: (today) => ({
    kind: 'week_rhythm',
    present_weeks: [FIRST_WEEK],
    cycle_weeks: DEFAULT_RHYTHM_CYCLE,
    change_weekday: DEFAULT_RHYTHM_CHANGE_DAY,
    anchor: dayOf(today),
  }),
  recurring: (today) => ({
    kind: 'recurring',
    weekdays: DEFAULT_RECURRING_ABSENCE_WEEKDAYS,
    interval_weeks: DEFAULT_RECURRENCE_INTERVAL,
    start: dayOf(today),
    end: null,
  }),
};

/** Neuer Eintrag eines Zeitplans: die Aufgabe mindestens einmal je Lauf. */
export function newEntry(taskId: string): EntryWire {
  return { task_id: taskId, mode: 'min_count', min_count: DEFAULT_MIN_COUNT };
}

/** Standard-Intervall neuer Zeitpläne: alle sieben Tage. */
export const INTERVAL_DEFAULT: IntervalWire = { unit: 'day', every: DEFAULT_INTERVAL_EVERY };

/** Erster Termin eines neuen Zeitplans: die nächste volle Stunde nach `now` (ISO). */
export function defaultStart(now: string): string {
  const next = Math.ceil(
    (Date.parse(now) + MS_PER_HOUR * DEFAULT_START_OFFSET_HOURS) / MS_PER_HOUR,
  );
  return new Date(next * MS_PER_HOUR).toISOString();
}
