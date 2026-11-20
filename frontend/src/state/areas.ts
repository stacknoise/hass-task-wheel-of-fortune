import type { AreaOption } from '../api/index.ts';

/** Anzeigenamen der Räume nach Kennung. */
export type AreaNames = ReadonlyMap<string, string>;

const tables = new WeakMap<readonly AreaOption[], AreaNames>();

/** Räume als Nachschlagetabelle Kennung → Name; dieselbe Liste ergibt dieselbe Tabelle. */
export function areaNames(areas: readonly AreaOption[]): AreaNames {
  let table = tables.get(areas);
  if (table === undefined) {
    table = new Map(areas.map((area) => [area.id, area.label]));
    tables.set(areas, table);
  }
  return table;
}

/** Ein Raum einer Aufgabe zur Anzeige; `deleted` heißt: Home Assistant kennt den Raum nicht mehr. */
export interface RoomRef {
  readonly name: string;
  readonly deleted: boolean;
}

/**
 * Die Räume einer Aufgabe für die Anzeige; ohne Raum leer.
 *
 * Ein Raum, den Home Assistant nicht mehr kennt (gelöscht), zeigt `unknown` statt der Kennung.
 */
export function roomRefsOf(
  areas: AreaNames,
  areaIds: readonly string[] | null | undefined,
  unknown: string,
): readonly RoomRef[] {
  return (areaIds ?? []).map((id) => {
    const name = areas.get(id);
    return name === undefined ? { name: unknown, deleted: true } : { name, deleted: false };
  });
}

/** Namen der Räume einer Aufgabe für die Anzeige als Text (siehe `roomRefsOf`). */
export function roomsOf(
  areas: AreaNames,
  areaIds: readonly string[] | null | undefined,
  unknown: string,
): readonly string[] {
  return roomRefsOf(areas, areaIds, unknown).map((room) => room.name);
}
