/** Typisierte Sicht auf die Objekte und Antworten der WebSocket-API (KONZEPT §6.4). */

import type { AssignmentStatus } from '../constants/index.ts';
import type { Snapshot, WireObject } from './types.ts';

export interface PersonObject extends WireObject {
  readonly name: string;
  readonly color: string;
  readonly load: string;
  readonly jokers_left: number;
}

export interface TaskObject extends WireObject {
  readonly name: string;
  readonly allowed: readonly string[];
  readonly points: number;
  readonly swap_allowed: boolean;
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
  readonly closed: number;
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

export type Matrix = Readonly<Record<string, Readonly<Record<string, number>>>>;

export interface StatisticsReport {
  readonly months: readonly string[];
  readonly kpis: Kpis;
  readonly standings: readonly Standing[];
  readonly fairness_index: number;
  readonly matrix: Matrix;
  readonly weeks: readonly WeekRate[];
  readonly highlights: Highlights;
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
