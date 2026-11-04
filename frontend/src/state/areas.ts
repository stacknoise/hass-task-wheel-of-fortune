import type { AreaOption } from '../api/index.ts';

/** Anzeigenamen der Räume nach Kennung. */
export type AreaNames = ReadonlyMap<string, string>;

/** Räume als Nachschlagetabelle Kennung → Name. */
export function areaNames(areas: readonly AreaOption[]): AreaNames {
  return new Map(areas.map((area) => [area.id, area.label]));
}

/**
 * Namen der Räume einer Aufgabe für die Anzeige; ohne Raum leer.
 *
 * Ein Raum, den Home Assistant nicht mehr kennt (gelöscht), zeigt `unknown` statt der Kennung.
 */
export function roomsOf(
  areas: AreaNames,
  areaIds: readonly string[] | null | undefined,
  unknown: string,
): readonly string[] {
  return (areaIds ?? []).map((id) => areas.get(id) ?? unknown);
}
