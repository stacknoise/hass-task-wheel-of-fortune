import { DRAW_PHASE, EMPTY_TEXT } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { DrawState, PersonInfo, ScheduleInfo } from '../state/index.ts';

/** Name des Zeitplans, sonst leer. */
export function nameOf(schedules: readonly ScheduleInfo[], id: string | undefined): string {
  return schedules.find((schedule) => schedule.id === id)?.name ?? EMPTY_TEXT;
}

/**
 * Wer noch auf eine Aufgabe wartet: alle Personen der Runde ohne Aufgabe. Wer sie tatsächlich
 * bekommen darf, bleibt für die Zuseher verdeckt; das Ergebnis des laufenden Dreh zählt noch nicht.
 */
export function waitingPersons(
  state: DrawState,
  persons: ReadonlyMap<string, PersonInfo>,
): readonly PersonInfo[] {
  const taken = new Set(
    state.results.filter((result) => result !== state.current).map((result) => result.winner_id),
  );
  return [...persons.values()].filter((person) => !taken.has(person.id));
}

/** Ist die Aufgabe an dieser Stelle der Runde gerade dran? */
export function isCurrentTask(state: DrawState, index: number, shown: number): boolean {
  return index === shown && state.phase !== DRAW_PHASE.done;
}

/** Die Person, der die Aufgabe an dieser Stelle schon zugeteilt wurde, sonst nichts. */
export function winnerOf(
  state: DrawState,
  persons: ReadonlyMap<string, PersonInfo>,
  index: number,
  shown: number,
): PersonInfo | undefined {
  return index < shown ? persons.get(state.results[index]?.winner_id ?? EMPTY_TEXT) : undefined;
}

/** Was in der Aufgabenliste als Status steht: „nicht verteilbar“, „ist dran“ oder „wartet“. */
export function taskStatus(
  state: DrawState,
  index: number,
  shown: number,
  language: string,
): string {
  if (index < shown) {
    return translate('draw.undistributable', language);
  }
  return translate(isCurrentTask(state, index, shown) ? 'draw.current' : 'draw.waiting', language);
}
