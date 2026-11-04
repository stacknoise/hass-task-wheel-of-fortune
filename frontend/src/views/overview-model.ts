import type {
  AssignmentObject,
  PersonObject,
  RoundHead,
  RoundObject,
  ScheduleObject,
  TaskObject,
} from '../api/index.ts';
import { FILTER_ALL, LOAD_PAUSED, STATUS } from '../constants/index.ts';
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

/** Ein möglicher Tauschpartner: die Person und ihre offene Zuteilung (samt Aufgabe). */
export interface SwapTarget {
  readonly person: PersonObject;
  readonly assignment: AssignmentObject;
  readonly task: TaskObject | undefined;
}

/** Vorfilter je Richtung: Aufgaben erlauben den Tausch, die Zielperson ist nicht pausiert. */
function swapPossible(
  assignment: AssignmentObject,
  task: TaskObject | undefined,
  person: PersonObject,
  other: TaskObject | undefined,
): boolean {
  return (
    person.load !== LOAD_PAUSED &&
    (other?.swap_allowed ?? false) &&
    allowsPerson(new Set(task?.allowed ?? []), person.id) &&
    allowsPerson(new Set(other?.allowed ?? []), assignment.person_id)
  );
}

/**
 * Tauschpartner: Personen derselben Auslosung mit einer offenen Zuteilung (bei mehreren die mit
 * der frühesten Frist, wie im Backend). Beide Aufgaben müssen den Tausch erlauben und die jeweils
 * andere Person zulassen; nicht man selbst, die Zielperson nicht pausiert.
 */
export function swapTargets(
  assignment: AssignmentObject,
  task: TaskObject | undefined,
  roundAssignments: readonly AssignmentObject[],
  persons: readonly PersonObject[],
  taskById: ReadonlyMap<string, TaskObject>,
): readonly SwapTarget[] {
  const personById = new Map(persons.map((person) => [person.id, person]));
  const earliestFirst = roundAssignments
    .filter(
      (item) =>
        item.round_id === assignment.round_id &&
        item.status === STATUS.open &&
        item.person_id !== assignment.person_id,
    )
    .sort((a, b) => a.due_at.localeCompare(b.due_at));
  const seen = new Set<string>();
  const targets: SwapTarget[] = [];
  for (const item of earliestFirst) {
    const person = personById.get(item.person_id);
    const other = taskById.get(item.task_id);
    if (person && !seen.has(person.id) && swapPossible(assignment, task, person, other)) {
      targets.push({ person, assignment: item, task: other });
    }
    seen.add(item.person_id);
  }
  return targets;
}

/** Ob getauscht werden kann: die Aufgabe erlaubt es und die Zuteilung ist noch offen (nicht schon getauscht). */
export function canSwap(task: TaskObject | undefined, assignment: AssignmentObject): boolean {
  return (task?.swap_allowed ?? false) && assignment.status === STATUS.open;
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
