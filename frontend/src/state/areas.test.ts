import { describe, expect, it } from 'vitest';

import { areaNames, roomOf } from './areas.ts';

const AREAS = areaNames([
  { id: 'kueche', label: 'Küche' },
  { id: 'bad', label: 'Bad' },
]);

describe('roomOf', () => {
  it('liefert den Namen des Raums', () => {
    expect(roomOf(AREAS, 'kueche', '?')).toBe('Küche');
  });
  it('bleibt ohne Raum leer', () => {
    expect(roomOf(AREAS, null, '?')).toBe('');
    expect(roomOf(AREAS, undefined, '?')).toBe('');
    expect(roomOf(AREAS, '', '?')).toBe('');
  });
  it('zeigt einen gelöschten Raum als unbekannt', () => {
    expect(roomOf(AREAS, 'keller', 'Unbekannter Raum')).toBe('Unbekannter Raum');
  });
});
