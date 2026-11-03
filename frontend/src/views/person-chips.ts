import type { PersonObject } from '../api/index.ts';
import type { ChipItem } from '../components/index.ts';
import { FILTER_ALL } from '../constants/index.ts';

/** Auswahl „Alle“ plus eine Marke je Person in ihrer Farbe. */
export function personChips(
  persons: readonly PersonObject[],
  allLabel: string,
): readonly ChipItem[] {
  return [
    { id: FILTER_ALL, label: allLabel },
    ...persons.map((person) => ({ id: person.id, label: person.name, color: person.color })),
  ];
}
