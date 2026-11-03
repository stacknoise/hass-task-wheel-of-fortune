import type {
  AssignmentObject,
  PersonObject,
  RoundHead,
  RoundObject,
  ScheduleObject,
  TaskObject,
} from '../api/index.ts';
import { FILTER_ALL, LOAD_PAUSED } from '../constants/index.ts';
import { allowsPerson } from '../state/index.ts';

export interface AssignmentGroup {
  /** Die Auslosung; leer bei Zuteilungen, deren Runde nicht mehr bekannt ist. */
  readonly round: RoundHead | undefined;
  /** Der Zeitplan der Auslosung; leer, wenn es ihn nicht mehr gibt. */
  readonly schedule: ScheduleObject | undefined;
  readonly assignments: readonly AssignmentObject[];
}

/** Zeitpläne mit geplanter Auslosung, die nächste zuerst. */
export function upcomingDraws(schedules: readonly ScheduleObject[]): readonly ScheduleObject[] {
  return schedules
    .filter((schedule) => schedule.enabled && !schedule.archived && schedule.next_run !== null)
    .sort((a, b) => (a.next_run ?? '').localeCompare(b.next_run ?? ''));
}

/** Zuteilungen der gewählten Person (oder aller). */
export function filterByPerson(
  assignments: readonly AssignmentObject[],
  personId: string,
): readonly AssignmentObject[] {
  return personId === FILTER_ALL
    ? assignments
    : assignments.filter((assignment) => assignment.person_id === personId);
}

/**
 * Gruppiert nach Auslosung, die jüngste zuerst. Der Kopf der Runde nennt Zeitplan und Beginn;
 * Zuteilungen ohne bekannte Runde stehen am Ende.
 */
export function groupByRound(
  assignments: readonly AssignmentObject[],
  rounds: readonly RoundHead[],
  schedules: readonly ScheduleObject[],
): readonly AssignmentGroup[] {
  const scheduleById = new Map(schedules.map((schedule) => [schedule.id, schedule]));
  const known = new Set(rounds.map((round) => round.id));
  const newestFirst = [...rounds].sort((a, b) => b.started_at.localeCompare(a.started_at));
  const heads: (RoundHead | undefined)[] = [...newestFirst, undefined];
  return heads
    .map((round) => ({
      round,
      schedule: round && scheduleById.get(round.schedule_id),
      assignments: assignments.filter((assignment) =>
        round ? assignment.round_id === round.id : !known.has(assignment.round_id),
      ),
    }))
    .filter((group) => group.assignments.length > 0);
}

/**
 * Personen, auf die getauscht werden darf: in derselben Auslosung, erlaubt für die Aufgabe, nicht
 * die jetzige, nicht pausiert.
 */
export function swapTargets(
  assignment: AssignmentObject,
  task: TaskObject | undefined,
  persons: readonly PersonObject[],
  roundPersonIds: readonly string[],
): readonly PersonObject[] {
  const allowed = new Set(task?.allowed ?? []);
  const inRound = new Set(roundPersonIds);
  return persons.filter(
    (person) =>
      inRound.has(person.id) &&
      allowsPerson(allowed, person.id) &&
      person.id !== assignment.person_id &&
      person.load !== LOAD_PAUSED,
  );
}

/** Ob getauscht werden kann: Aufgabe erlaubt es, die Person hat noch einen Joker. */
export function canSwap(task: TaskObject | undefined, person: PersonObject | undefined): boolean {
  return (task?.swap_allowed ?? false) && (person?.jokers_left ?? 0) > 0;
}

export interface ActivityItem {
  readonly assignment: AssignmentObject;
  readonly at: string;
}

/** Die jüngsten Ereignisse aus den Runden: erledigt zur Erledigungszeit, sonst zum Rundenbeginn. */
export function recentActivity(
  rounds: readonly RoundObject[],
  count: number,
): readonly ActivityItem[] {
  return rounds
    .flatMap((round) =>
      round.assignments.map((assignment) => ({
        assignment,
        at: assignment.done_at ?? round.started_at,
      })),
    )
    .sort((a, b) => b.at.localeCompare(a.at))
    .slice(0, count);
}
