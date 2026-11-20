import { personsOf, tasksOf } from '../api/index.ts';
import type { Snapshot } from '../api/index.ts';
import type { ChipOption } from '../components/index.ts';

/** Die Personen als Auswahlpunkte (mit ihrer Farbe). */
export function personOptions(snapshot: Snapshot): readonly ChipOption[] {
  return personsOf(snapshot).map((person) => ({
    id: person.id,
    label: person.name,
    color: person.color,
  }));
}

/** Die Aufgaben als Auswahlpunkte. */
export function taskOptions(snapshot: Snapshot): readonly ChipOption[] {
  return tasksOf(snapshot).map((task) => ({ id: task.id, label: task.name }));
}
