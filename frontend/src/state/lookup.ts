import type { PanelRoundWire, Snapshot, WireObject } from '../api/index.ts';
import { EMPTY_TEXT, FALLBACK_COLOR } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import { animationsOf } from './animation.ts';

export interface PersonInfo {
  readonly id: string;
  readonly name: string;
  readonly color: string;
}

export interface TaskInfo {
  readonly id: string;
  readonly name: string;
  readonly points: number;
  readonly dueDays: number;
  readonly allowed: ReadonlySet<string>;
}

export interface ScheduleInfo {
  readonly id: string;
  readonly name: string;
  readonly archived: boolean;
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
      color: text(item, 'color', FALLBACK_COLOR),
    })),
  );
}

export function tasksById(snapshot: Snapshot): ReadonlyMap<string, TaskInfo> {
  return indexById(
    snapshot.tasks.map((item) => ({
      id: item.id,
      name: text(item, 'name', item.id),
      points: count(item, 'points'),
      dueDays: count(item, 'due_days'),
      allowed: new Set(texts(item, 'allowed')),
    })),
  );
}

/** Zeitpläne, die sich auslosen lassen (nicht archiviert). */
export function drawableSchedules(snapshot: Snapshot): readonly ScheduleInfo[] {
  return snapshot.schedules
    .map((item) => ({
      id: item.id,
      name: text(item, 'name', item.id),
      archived: item['archived'] === true,
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

/** Personen der Runde: nur wer für mindestens eine ihrer Aufgaben erlaubt ist (ohne Runde: alle). */
export function participantsOf(
  persons: ReadonlyMap<string, PersonInfo>,
  tasks: ReadonlyMap<string, TaskInfo>,
  taskIds: readonly string[],
): ReadonlyMap<string, PersonInfo> {
  const roundTasks = taskIds.flatMap((id) => tasks.get(id) ?? []);
  if (roundTasks.length === 0) {
    return persons;
  }
  return new Map(
    [...persons].filter(([id]) => roundTasks.some((task) => allowsPerson(task.allowed, id))),
  );
}

/** Die offene Panel-Runde des Zeitplans, falls es eine gibt. */
export function openRoundFor(snapshot: Snapshot, scheduleId: string): PanelRoundWire | undefined {
  return (snapshot.panel_rounds as readonly unknown[] as readonly PanelRoundWire[]).find(
    (round) => round.schedule_id === scheduleId,
  );
}
