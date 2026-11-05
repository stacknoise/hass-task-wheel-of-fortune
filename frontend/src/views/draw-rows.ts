import type { TaskDrawWire } from '../api/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import { formatPercent } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { allowsPerson } from '../state/index.ts';
import type { PersonInfo, ScheduleInfo, TaskInfo } from '../state/index.ts';

const NOT_ALLOWED = 'not_allowed';

/** Name des Zeitplans, sonst leer. */
export function nameOf(schedules: readonly ScheduleInfo[], id: string | undefined): string {
  return schedules.find((schedule) => schedule.id === id)?.name ?? EMPTY_TEXT;
}

export interface Row {
  readonly person: PersonInfo;
  readonly note: string;
  readonly inWheel: boolean;
}

/** Jede Person mit ihrer Chance oder dem Grund, warum sie nicht im Rad ist. */
export function personRows(
  result: TaskDrawWire | undefined,
  task: TaskInfo | undefined,
  persons: ReadonlyMap<string, PersonInfo>,
  showChance: boolean,
  language: string,
): readonly Row[] {
  const chances = new Map(result?.segments.map((segment) => [segment.person_id, segment.chance]));
  const reasons = new Map(result?.exclusions.map((item) => [item.person_id, item.reason]));
  return [...persons.values()].map((person) => {
    const chance = chances.get(person.id);
    if (chance !== undefined) {
      return {
        person,
        inWheel: true,
        note: showChance ? formatPercent(chance, language) : EMPTY_TEXT,
      };
    }
    const allowed = task ? allowsPerson(task.allowed, person.id) : false;
    const reason = allowed ? reasons.get(person.id) : NOT_ALLOWED;
    return {
      person,
      inWheel: !result && allowed,
      note: reason ? translate(`draw.reason.${reason}` as TextKey, language) : EMPTY_TEXT,
    };
  });
}
