/** Typisierte Sicht auf die Objekte und Antworten der WebSocket-API (KONZEPT §6.4). */

import type { AssignmentStatus, Period } from '../constants/index.ts';
import type { Snapshot, WireObject } from './types.ts';

export interface PersonObject extends WireObject {
  readonly name: string;
  readonly color: string;
  readonly load: string;
}

export interface TaskObject extends WireObject {
  readonly name: string;
  readonly allowed: readonly string[];
  readonly points: number;
  readonly swap_allowed: boolean;
  /** Kennungen der Home-Assistant-Bereiche (Räume) der Aufgabe. */
  readonly area_ids?: readonly string[];
}

export interface ScheduleObject extends WireObject {
  readonly name: string;
  readonly task_ids: readonly string[];
  readonly enabled: boolean;
  readonly archived: boolean;
  readonly next_run: string | null;
}

export interface AssignmentObject extends WireObject {
  readonly round_id: string;
  /** Der Zeitplan, der die Zuteilung ausgelost hat. */
  readonly schedule_id: string;
  readonly task_id: string;
  readonly person_id: string;
  readonly chance: number;
  readonly points: number;
  readonly due_at: string;
  readonly status: AssignmentStatus;
  readonly done_at: string | null;
}

/** Kopf einer Auslosung mit offenen Zuteilungen (Sammlung `rounds` des Snapshots). */
export interface RoundHead extends WireObject {
  readonly schedule_id: string;
  readonly origin: string;
  readonly started_at: string;
  readonly total: number;
  /** Erledigte (pünktlich oder verspätet) Zuteilungen; dann ist Löschen gesperrt. */
  readonly done: number;
}

export interface RoundObject extends WireObject {
  readonly schedule_id: string;
  readonly origin: string;
  readonly started_at: string;
  readonly assignments: readonly AssignmentObject[];
}

export interface HistoryPage {
  readonly entries: readonly RoundObject[];
  readonly next_offset: number | null;
}

/** Eine Person im Rad einer Aufgabe, mit dem Namen zum Zeitpunkt der Entscheidung. */
export interface DecisionWheelEntry {
  readonly person_id: string;
  readonly person_name: string;
  readonly chance: number;
}

/** Eine Person, die nicht im Rad war, mit dem Grund (Schlüssel `ExclusionReason` oder `not_allowed`). */
export interface DecisionExcluded {
  readonly person_id: string;
  readonly person_name: string;
  readonly reason: string;
}

/** Ausgang einer Auslosung für eine Aufgabe; ohne `winner_id` blieb sie unvergeben. */
export interface DecisionTask {
  readonly task_id: string;
  readonly task_name: string;
  readonly winner_id: string | null;
  readonly wheel: readonly DecisionWheelEntry[];
  readonly excluded: readonly DecisionExcluded[];
}

/** Tausch zweier Personen oder Austausch einer Aufgabe; `before_start` markiert den Admin-Austausch vor dem Start. */
export interface DecisionExchange {
  readonly person_id: string;
  readonly person_name: string;
  readonly task_id: string;
  readonly task_name: string;
  readonly other_task_id: string;
  readonly other_task_name: string;
  readonly other_person_id: string | null;
  readonly other_person_name: string | null;
  readonly before_start: boolean;
}

/** Ein Eintrag des Entscheidungslogs. */
export interface DecisionRecord {
  readonly id: string;
  readonly kind: string;
  readonly at: string;
  readonly schedule_id: string;
  readonly schedule_name: string;
  readonly round_id: string | null;
  readonly origin: string | null;
  readonly tasks: readonly DecisionTask[];
  readonly exchange: DecisionExchange | null;
}

export interface DecisionPage {
  readonly entries: readonly DecisionRecord[];
  readonly next_offset: number | null;
}

export interface DecisionQuery {
  readonly schedule_id?: string;
  readonly person_id?: string;
  readonly offset?: number;
  readonly limit?: number;
}

export interface HistoryQuery {
  readonly person_id?: string;
  readonly offset?: number;
  readonly limit?: number;
}

export interface Kpis {
  readonly assigned: number;
  readonly on_time: number;
  readonly late: number;
  readonly missed: number;
  readonly pending: number;
  readonly completion_rate: number | null;
}

export interface Standing {
  readonly person_id: string;
  readonly points: number;
  readonly fair_points: number;
  readonly difference: number;
}

export interface WeekRate {
  readonly week_start: string;
  readonly done: number;
  readonly missed: number;
  readonly rate: number | null;
}

export interface Reliable {
  readonly person_id: string;
  readonly on_time_rate: number;
  readonly closed: number;
}

export interface Highlights {
  readonly lucky: string | null;
  readonly unlucky: string | null;
  readonly reliable: Reliable | null;
}

export interface GoalWindow {
  readonly start: string;
  readonly end: string;
  readonly assigned: number;
  readonly done: number;
}

export interface TaskGoal {
  readonly task_id: string;
  readonly target: number;
  readonly period: Period;
  readonly every: number;
  readonly windows: readonly GoalWindow[];
}

export type Matrix = Readonly<Record<string, Readonly<Record<string, number>>>>;

export interface StatisticsReport {
  readonly months: readonly string[];
  readonly kpis: Kpis;
  readonly standings: readonly Standing[];
  readonly fairness_index: number;
  readonly matrix: Matrix;
  readonly weeks: readonly WeekRate[];
  readonly highlights: Highlights;
  readonly goals: readonly TaskGoal[];
}

/** Die Objekte der Sammlungen mit ihren bekannten Feldern. */
export interface ModelsOf {
  readonly persons: PersonObject;
  readonly tasks: TaskObject;
  readonly schedules: ScheduleObject;
  readonly assignments: AssignmentObject;
  readonly rounds: RoundHead;
}

/** Sicht auf eine Sammlung des Snapshots; die Form der Objekte garantiert das Backend (KONZEPT §6.4). */
export function modelsOf<K extends keyof ModelsOf>(
  snapshot: Snapshot,
  name: K,
): readonly ModelsOf[K][] {
  return snapshot[name].map((item) => item as ModelsOf[K]);
}
