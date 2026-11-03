import type { WireObject } from '../api/index.ts';

/** Objekte nach Kennung, um Verweise (Person, Aufgabe, Zeitplan) aufzulösen. */
export function indexById<T extends WireObject>(items: readonly T[]): ReadonlyMap<string, T> {
  return new Map(items.map((item) => [item.id, item]));
}
