/** Formen der Konfigurationsobjekte auf der Leitung (KONZEPT §4); Zeiten und Daten als ISO-Text. */

import type {
  AbsenceKind,
  AfterOnce,
  AnimationKind,
  FrequencyKind,
  Load,
  Period,
  TriggerKind,
} from '../constants/index.ts';

export interface OnceAbsenceWire {
  readonly kind: Extract<AbsenceKind, 'once'>;
  readonly start: string;
  readonly end: string;
}

export interface WeeklyDaysAbsenceWire {
  readonly kind: Extract<AbsenceKind, 'weekly_days'>;
  readonly weekdays: readonly number[];
}

export interface WeekRhythmAbsenceWire {
  readonly kind: Extract<AbsenceKind, 'week_rhythm'>;
  readonly present_weeks: readonly number[];
  readonly cycle_weeks: number;
  readonly change_weekday: number;
  readonly anchor: string;
}

export interface RecurringAbsenceWire {
  readonly kind: Extract<AbsenceKind, 'recurring'>;
  readonly weekdays: readonly number[];
  readonly interval_weeks: number;
  readonly start: string;
  /** Letzter Tag der Wiederholung; `null` heißt ohne Ende. */
  readonly end: string | null;
}

export type AbsenceWire =
  OnceAbsenceWire | WeeklyDaysAbsenceWire | WeekRhythmAbsenceWire | RecurringAbsenceWire;

export interface EveryRoundWire {
  readonly kind: Extract<FrequencyKind, 'every_round'>;
}

export interface MaxPerPeriodWire {
  readonly kind: Extract<FrequencyKind, 'max_per_period'>;
  readonly count: number;
  readonly period: Period;
  readonly every: number;
}

export interface IntervalWire {
  readonly kind: Extract<FrequencyKind, 'interval'>;
  readonly days: number;
  readonly tolerance: number;
}

export type FrequencyWire = EveryRoundWire | MaxPerPeriodWire | IntervalWire;

export interface RecurringWire {
  readonly kind: Extract<TriggerKind, 'recurring'>;
  readonly weekdays: readonly number[];
  readonly time: string;
  readonly every_n_weeks: number;
  readonly monthly: boolean;
  readonly anchor: string | null;
}

export interface OnceTriggerWire {
  readonly kind: Extract<TriggerKind, 'once'>;
  readonly at: string;
  readonly after: AfterOnce;
}

export interface ManualTriggerWire {
  readonly kind: Extract<TriggerKind, 'manual'>;
  readonly remind_after_days: number | null;
}

export type TriggerWire = RecurringWire | OnceTriggerWire | ManualTriggerWire;

export interface PersonWire {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly color: string;
  readonly load: Load;
  readonly absences: readonly AbsenceWire[];
  readonly notify_target: string | null;
}

export interface TaskWire {
  readonly id: string;
  readonly name: string;
  readonly allowed: readonly string[];
  readonly frequency: FrequencyWire;
  readonly points: number;
  readonly due_days: number;
  readonly no_repeat: boolean;
  readonly respect_absence: boolean;
  readonly swap_allowed: boolean;
  readonly min_load: Load;
  /** Kennungen der Home-Assistant-Bereiche (Räume); leer = kein Raum. */
  readonly area_ids: readonly string[];
}

export interface ScheduleWire {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly trigger: TriggerWire;
  readonly task_ids: readonly string[];
  readonly enabled: boolean;
  readonly notify: boolean;
  readonly skip_absent: boolean;
  readonly archived: boolean;
  readonly animations: readonly AnimationKind[];
}
