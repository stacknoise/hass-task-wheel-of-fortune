import { personsOf, tasksOf } from '../api/index.ts';
import type { Snapshot } from '../api/index.ts';
import type { ChipOption } from '../components/index.ts';
import { roomRefsOf } from '../state/index.ts';
import type { AreaNames } from '../state/index.ts';

/** Die Personen als Auswahlpunkte (mit ihrer Farbe). */
export function personOptions(snapshot: Snapshot): readonly ChipOption[] {
  return personsOf(snapshot).map((person) => ({
    id: person.id,
    label: person.name,
    color: person.color,
  }));
}

/** Die Aufgaben als Auswahlpunkte (mit ihren Räumen; `unknown` steht für einen gelöschten Raum). */
export function taskOptions(
  snapshot: Snapshot,
  areas: AreaNames,
  unknown: string,
): readonly ChipOption[] {
  return tasksOf(snapshot).map((task) => ({
    id: task.id,
    label: task.name,
    rooms: roomRefsOf(areas, task.area_ids, unknown),
  }));
}
