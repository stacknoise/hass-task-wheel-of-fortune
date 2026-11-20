/** Formen der Konfigurationsobjekte auf der Leitung (KONZEPT §4); Zeiten und Daten als ISO-Text. */

import type {
  AbsenceKind,
  AnimationKind,
  EntryMode,
  IntervalUnit,
  Load,
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
  readonly points: number;
  readonly no_repeat: boolean;
  readonly respect_absence: boolean;
  readonly swap_allowed: boolean;
  readonly min_load: Load;
  /** Kennungen der Home-Assistant-Bereiche (Räume); leer = kein Raum. */
  readonly area_ids: readonly string[];
}

/** Abstand zwischen zwei Auslosungen: alle `every` Stunden, Tage oder Wochen. */
export interface IntervalWire {
  readonly unit: IntervalUnit;
  readonly every: number;
}

/** Eine Aufgabe im Zeitplan: mindestens `min_count`× je Lauf oder in jeder Auslosung. */
export interface EntryWire {
  readonly task_id: string;
  readonly mode: EntryMode;
  readonly min_count: number;
}

export interface ScheduleWire {
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  /** Zeitpunkt der ersten Auslosung (ISO mit Zeitzone). */
  readonly start: string;
  readonly interval: IntervalWire;
  readonly automatic: boolean;
  /** Länge eines Laufs in Tagen; so lange gilt die Mindesthäufigkeit. */
  readonly run_days: number;
  readonly entries: readonly EntryWire[];
  readonly enabled: boolean;
  readonly notify: boolean;
  readonly skip_absent: boolean;
  readonly archived: boolean;
  readonly animations: readonly AnimationKind[];
}
