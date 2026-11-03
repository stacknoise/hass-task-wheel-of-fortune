import type {
  AssignmentObject,
  PersonObject,
  RoundObject,
  ScheduleObject,
  TaskObject,
} from '../api/index.ts';
import { DONE_STATUSES, PERCENT } from '../constants/index.ts';
import { formatDateTime } from '../i18n/format.ts';
import type { TextKey } from '../i18n/index.ts';

export interface HistoryLookups {
  readonly persons: ReadonlyMap<string, PersonObject>;
  readonly tasks: ReadonlyMap<string, TaskObject>;
  readonly schedules: ReadonlyMap<string, ScheduleObject>;
}

type Translate = (key: TextKey) => string;

const ORIGIN_KEYS: Readonly<Record<string, TextKey>> = {
  auto: 'history.origin.auto',
  manual: 'history.origin.manual',
  service: 'history.origin.service',
};

const HEADER_KEYS: readonly TextKey[] = [
  'history.round',
  'history.schedule',
  'history.origin',
  'history.startedAt',
  'history.task',
  'history.person',
  'history.chance',
  'history.points',
  'history.status',
  'history.doneAt',
];

/** Anzahl der Zuteilungen, die erledigt wurden (pünktlich oder verspätet). */
export function doneCount(assignments: readonly AssignmentObject[]): number {
  return assignments.filter((assignment) => DONE_STATUSES.includes(assignment.status)).length;
}

/** Text der Herkunft einer Runde; Unbekanntes wird unverändert angezeigt. */
export function originText(origin: string, text: Translate): string {
  const key = ORIGIN_KEYS[origin];
  return key ? text(key) : origin;
}

/** Zeilen der CSV-Datei: Kopfzeile und je Zuteilung eine Zeile mit den Angaben der Runde. */
export function csvRows(
  rounds: readonly RoundObject[],
  lookups: HistoryLookups,
  language: string,
  text: Translate,
): readonly (readonly string[])[] {
  const header = HEADER_KEYS.map((key) => text(key));
  const body = rounds.flatMap((round) =>
    round.assignments.map((assignment) => [
      round.id,
      lookups.schedules.get(round.schedule_id)?.name ?? text('common.unknownSchedule'),
      originText(round.origin, text),
      formatDateTime(round.started_at, language),
      lookups.tasks.get(assignment.task_id)?.name ?? text('common.unknownTask'),
      lookups.persons.get(assignment.person_id)?.name ?? text('common.unknownPerson'),
      String(Math.round(assignment.chance * PERCENT)),
      String(assignment.points),
      text(`status.${assignment.status}`),
      assignment.done_at ? formatDateTime(assignment.done_at, language) : '',
    ]),
  );
  return [header, ...body];
}
