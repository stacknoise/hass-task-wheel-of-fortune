import { describe, expect, it } from 'vitest';

import { areaNames, roomsOf } from './areas.ts';

const AREAS = areaNames([
  { id: 'kueche', label: 'Küche' },
  { id: 'bad', label: 'Bad' },
]);

describe('roomsOf', () => {
  it('liefert die Namen aller Räume in der Reihenfolge der Aufgabe', () => {
    expect(roomsOf(AREAS, ['kueche', 'bad'], '?')).toEqual(['Küche', 'Bad']);
  });
  it('bleibt ohne Raum leer', () => {
    expect(roomsOf(AREAS, [], '?')).toEqual([]);
    expect(roomsOf(AREAS, null, '?')).toEqual([]);
    expect(roomsOf(AREAS, undefined, '?')).toEqual([]);
  });
  it('zeigt einen gelöschten Raum als unbekannt', () => {
    expect(roomsOf(AREAS, ['kueche', 'keller'], 'Unbekannter Raum')).toEqual([
      'Küche',
      'Unbekannter Raum',
    ]);
  });
});
