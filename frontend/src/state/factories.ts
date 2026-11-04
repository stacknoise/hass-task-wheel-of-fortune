/** Fabriken der Standardwerte je Art (Abwesenheit, Häufigkeit, Auslöser); die Tabellen ersetzen Verzweigungen. */

import type { AbsenceWire, DeadlineWire, FrequencyWire, TriggerWire } from '../api/index.ts';
import {
  DEADLINE_OFFSET_MIN,
  DEFAULT_ABSENT_WEEKDAYS,
  DEFAULT_DEADLINE_DURATION,
  DEFAULT_DEADLINE_TIME,
  DEFAULT_EVERY_N_WEEKS,
  DEFAULT_INTERVAL_DAYS,
  DEFAULT_PERIOD_COUNT,
  DEFAULT_PERIOD_EVERY,
  DEFAULT_RECURRENCE_INTERVAL,
  DEFAULT_RECURRING_ABSENCE_WEEKDAYS,
  DEFAULT_RECURRING_WEEKDAYS,
  DEFAULT_RHYTHM_CHANGE_DAY,
  DEFAULT_RHYTHM_CYCLE,
  DEFAULT_TIME,
  MS_PER_DAY,
} from '../constants/index.ts';
import type { AbsenceKind, FrequencyKind, TriggerKind } from '../constants/index.ts';
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

export const FREQUENCY_BUILDERS: Readonly<Record<FrequencyKind, () => FrequencyWire>> = {
  every_round: () => ({ kind: 'every_round' }),
  max_per_period: () => ({
    kind: 'max_per_period',
    count: DEFAULT_PERIOD_COUNT,
    period: 'week',
    every: DEFAULT_PERIOD_EVERY,
  }),
  interval: () => ({ kind: 'interval', days: DEFAULT_INTERVAL_DAYS, tolerance: 0 }),
};

/** Neuer Auslöser je Art; `now` ist der aktuelle Zeitpunkt (ISO). */
export const TRIGGER_BUILDERS: Readonly<Record<TriggerKind, (now: string) => TriggerWire>> = {
  recurring: () => ({
    kind: 'recurring',
    weekdays: DEFAULT_RECURRING_WEEKDAYS,
    time: DEFAULT_TIME,
    every_n_weeks: DEFAULT_EVERY_N_WEEKS,
    monthly: false,
    anchor: null,
  }),
  once: (now) => ({
    kind: 'once',
    at: new Date(Date.parse(now) + MS_PER_DAY).toISOString(),
    after: 'keep_manual',
  }),
  manual: () => ({ kind: 'manual', remind_after_days: null }),
};

/** Frist neuer Zeitpläne: ab der Auslosung, eine Woche lang (wie im Backend). */
export const DEADLINE_DEFAULT: DeadlineWire = {
  start: 'now',
  offset: DEADLINE_OFFSET_MIN,
  offset_unit: 'hour',
  time: DEFAULT_DEADLINE_TIME,
  weekday: 0,
  duration: DEFAULT_DEADLINE_DURATION,
  duration_unit: 'day',
};
