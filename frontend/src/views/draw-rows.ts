import type { TaskDrawWire } from '../api/index.ts';
import { percentText } from '../components/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { allowsPerson } from '../state/index.ts';
import type { PersonInfo, TaskInfo } from '../state/index.ts';

const NOT_ALLOWED = 'not_allowed';

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
  text: (key: TextKey) => string,
): readonly Row[] {
  const chances = new Map(result?.segments.map((segment) => [segment.person_id, segment.chance]));
  const reasons = new Map(result?.exclusions.map((item) => [item.person_id, item.reason]));
  return [...persons.values()].map((person) => {
    const chance = chances.get(person.id);
    if (chance !== undefined) {
      return { person, inWheel: true, note: percentText(chance) };
    }
    const allowed = task ? allowsPerson(task.allowed, person.id) : false;
    const reason = allowed ? reasons.get(person.id) : NOT_ALLOWED;
    return {
      person,
      inWheel: !result && allowed,
      note: reason ? text(`draw.reason.${reason}` as TextKey) : EMPTY_TEXT,
    };
  });
}
