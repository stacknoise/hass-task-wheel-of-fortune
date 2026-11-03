import type {
  AssignmentObject,
  PersonObject,
  RoundObject,
  ScheduleObject,
  TaskObject,
} from '../api/index.ts';
import { FILTER_ALL, LOAD_PAUSED } from '../constants/index.ts';

export interface AssignmentGroup {
  /** Der Zeitplan, zu dem die Aufgabe gehört; leer, wenn kein Zeitplan sie mehr enthält. */
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
 * Gruppiert nach dem auslosenden Zeitplan (`schedule_id` der Zuteilung) in der Reihenfolge der
 * Zeitpläne; Zuteilungen gelöschter Zeitpläne stehen zuletzt in einer Gruppe ohne Zeitplan.
 */
export function groupBySchedule(
  assignments: readonly AssignmentObject[],
  schedules: readonly ScheduleObject[],
): readonly AssignmentGroup[] {
  const groups = new Map<string | undefined, AssignmentObject[]>();
  for (const schedule of schedules) {
    groups.set(schedule.id, []);
  }
  groups.set(undefined, []);
  for (const assignment of assignments) {
    const key = groups.has(assignment.schedule_id) ? assignment.schedule_id : undefined;
    groups.get(key)?.push(assignment);
  }
  const byId = new Map(schedules.map((schedule) => [schedule.id, schedule]));
  return [...groups]
    .filter(([, items]) => items.length > 0)
    .map(([id, items]) => ({
      schedule: id === undefined ? undefined : byId.get(id),
      assignments: items,
    }));
}

/** Personen, auf die getauscht werden darf: erlaubt für die Aufgabe, nicht die jetzige, nicht pausiert. */
export function swapTargets(
  assignment: AssignmentObject,
  task: TaskObject | undefined,
  persons: readonly PersonObject[],
): readonly PersonObject[] {
  const allowed = new Set(task?.allowed ?? []);
  return persons.filter(
    (person) =>
      allowed.has(person.id) && person.id !== assignment.person_id && person.load !== LOAD_PAUSED,
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
