import type { AreaOption } from '../api/index.ts';

/** Anzeigenamen der Räume nach Kennung. */
export type AreaNames = ReadonlyMap<string, string>;

/** Räume als Nachschlagetabelle Kennung → Name. */
export function areaNames(areas: readonly AreaOption[]): AreaNames {
  return new Map(areas.map((area) => [area.id, area.label]));
}

/**
 * Raum einer Aufgabe für die Anzeige; ohne Raum leer.
 *
 * Ein Raum, den Home Assistant nicht mehr kennt (gelöscht), zeigt `unknown` statt der Kennung.
 */
export function roomOf(
  areas: AreaNames,
  areaId: string | null | undefined,
  unknown: string,
): string {
  return areaId ? (areas.get(areaId) ?? unknown) : '';
}
