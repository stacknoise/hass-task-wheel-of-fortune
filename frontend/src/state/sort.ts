import { compareText } from '../api/index.ts';
import type { Snapshot, WireObject } from '../api/index.ts';
import { KEY_NAME, SORTED_COLLECTIONS } from '../constants/index.ts';

function nameOf(item: WireObject): string {
  const name = item[KEY_NAME];
  return typeof name === 'string' ? name : '';
}

/**
 * Objekte nach Name, ohne Groß-/Kleinschreibung und nach der Sprache (stabil bei gleichem Namen).
 *
 * Ist die Liste schon geordnet, bleibt sie dieselbe (die Identität zeigt unveränderte Sammlungen).
 */
export function sortedByName<T extends WireObject>(
  items: readonly T[],
  language: string,
): readonly T[] {
  const compare = compareText(language);
  const ordered = items.every(
    (item, index) => index === 0 || compare(nameOf(items[index - 1] as T), nameOf(item)) <= 0,
  );
  return ordered ? items : [...items].sort((a, b) => compare(nameOf(a), nameOf(b)));
}

/** Personen, Aufgaben und Zeitpläne des Stands alphabetisch; alles andere bleibt unverändert. */
export function sortSnapshot(snapshot: Snapshot, language: string): Snapshot {
  const next = { ...snapshot };
  for (const name of SORTED_COLLECTIONS) {
    Object.assign(next, { [name]: sortedByName(snapshot[name], language) });
  }
  return next;
}
