import { describe, expect, it } from 'vitest';

import { EMPTY_SNAPSHOT } from '../api/fake-hass.testing.ts';
import { FALLBACK_COLOR } from '../constants/index.ts';
import { safeColor } from './color.ts';
import { personsById } from './lookup.ts';

describe('safeColor', () => {
  it('lässt Farben der Form #rrggbb durch', () => {
    expect(safeColor('#c05600')).toBe('#c05600');
    expect(safeColor('#C05600')).toBe('#C05600');
  });

  it.each(['red;position:fixed;inset:0', '#fff', 'url(x)', '', undefined, 7, null])(
    'ersetzt %j durch die Ersatzfarbe',
    (value) => {
      expect(safeColor(value)).toBe(FALLBACK_COLOR);
    },
  );

  it('wird schon beim Einlesen der Personen angewendet', () => {
    const persons = personsById({
      ...EMPTY_SNAPSHOT,
      persons: [{ id: 'p1', name: 'Anna', color: 'red;position:fixed' }],
    });
    expect(persons.get('p1')?.color).toBe(FALLBACK_COLOR);
  });
});
