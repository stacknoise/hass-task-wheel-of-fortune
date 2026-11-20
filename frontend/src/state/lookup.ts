import { schedulesOf } from '../api/index.ts';
import type { EntryWire, PanelRoundWire, Snapshot, WireObject } from '../api/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import { animationsOf } from './animation.ts';
import { safeColor } from './color.ts';

export interface PersonInfo {
  readonly id: string;
  readonly name: string;
  readonly color: string;
}

export interface TaskInfo {
  readonly id: string;
  readonly name: string;
  readonly points: number;
  readonly allowed: ReadonlySet<string>;
  /** Kennungen der Räume; leer = kein Raum. */
  readonly areaIds: readonly string[];
}

export interface ScheduleInfo {
  readonly id: string;
  readonly name: string;
  readonly archived: boolean;
  /** Termin der nächsten offenen Periode (ISO) oder `null`; bei manuellen Plänen kann er in der Vergangenheit liegen (= fällig). */
  readonly nextRun: string | null;
  /** Nummer der nächsten offenen Periode (0 = erste). */
  readonly nextPeriod: number;
  /** Erlaubte Animationen; bei jeder Auslosung wird zufällig eine gewählt. */
  readonly animations: readonly AnimationKind[];
}

function text(item: WireObject, field: string, fallback = EMPTY_TEXT): string {
  const value = item[field];
  return typeof value === 'string' ? value : fallback;
}

function count(item: WireObject, field: string): number {
  const value = item[field];
  return typeof value === 'number' ? value : 0;
}

function texts(item: WireObject, field: string): readonly string[] {
  const value = item[field];
  return Array.isArray(value) ? value.filter((entry) => typeof entry === 'string') : [];
}

/** Objekte nach Kennung, um Verweise (Person, Aufgabe, Zeitplan) aufzulösen. */
export function indexById<T extends { readonly id: string }>(
  items: readonly T[],
): ReadonlyMap<string, T> {
  return new Map(items.map((item) => [item.id, item]));
}

export function personsById(snapshot: Snapshot): ReadonlyMap<string, PersonInfo> {
  return indexById(
    snapshot.persons.map((item) => ({
      id: item.id,
      name: text(item, 'name', item.id),
      color: safeColor(item['color']),
    })),
  );
}

export function tasksById(snapshot: Snapshot): ReadonlyMap<string, TaskInfo> {
  return indexById(
    snapshot.tasks.map((item) => ({
      id: item.id,
      name: text(item, 'name', item.id),
      points: count(item, 'points'),
      allowed: new Set(texts(item, 'allowed')),
      areaIds: texts(item, 'area_ids'),
    })),
  );
}

/** In welchen Zeitplänen eine Aufgabe vorkommt und wie. */
export interface TaskUsage {
  readonly scheduleId: string;
  readonly scheduleName: string;
  readonly entry: EntryWire;
}

export function taskUsage(snapshot: Snapshot, taskId: string): readonly TaskUsage[] {
  return schedulesOf(snapshot).flatMap((schedule) =>
    schedule.entries
      .filter((entry) => entry.task_id === taskId)
      .map((entry) => ({ scheduleId: schedule.id, scheduleName: schedule.name, entry })),
  );
}

/** Zeitpläne, die sich auslosen lassen (nicht archiviert). */
export function drawableSchedules(snapshot: Snapshot): readonly ScheduleInfo[] {
  return snapshot.schedules
    .map((item) => ({
      id: item.id,
      name: text(item, 'name', item.id),
      archived: item['archived'] === true,
      nextRun: typeof item['next_run'] === 'string' ? item['next_run'] : null,
      nextPeriod: count(item, 'next_period'),
      animations: animationsOf(item['animations']),
    }))
    .filter((schedule) => !schedule.archived);
}

/** Ob die Person die Aufgabe bekommen darf (ohne erlaubte Personen: jede). */
export function allowsPerson(allowed: ReadonlySet<string>, personId: string): boolean {
  return allowed.size === 0 || allowed.has(personId);
}

/** Wie viele Personen die Aufgabe noch bekommen können (erlaubt und noch ohne Aufgabe der Runde). */
export function openCandidates(
  persons: ReadonlyMap<string, PersonInfo>,
  task: TaskInfo,
  taken: ReadonlySet<string | null>,
): number {
  return [...persons.keys()].filter((id) => allowsPerson(task.allowed, id) && !taken.has(id))
    .length;
}

/** Personen der Runde: nur wer laut Backend teilnimmt (ohne Runde: alle). */
export function participantsOf(
  persons: ReadonlyMap<string, PersonInfo>,
  participantIds: readonly string[],
): ReadonlyMap<string, PersonInfo> {
  if (participantIds.length === 0) {
    return persons;
  }
  const taking = new Set(participantIds);
  return new Map([...persons].filter(([id]) => taking.has(id)));
}

/** Die offene Panel-Runde des Zeitplans, falls es eine gibt. */
export function openRoundFor(snapshot: Snapshot, scheduleId: string): PanelRoundWire | undefined {
  return (snapshot.panel_rounds as readonly unknown[] as readonly PanelRoundWire[]).find(
    (round) => round.schedule_id === scheduleId,
  );
}
