import { describe, expect, it } from 'vitest';

import { ROOM_COLORS } from '../constants/index.ts';
import { roomHue } from './room-color.ts';

describe('roomHue', () => {
  it('ist für denselben Namen gleich und liegt im Farbkreis', () => {
    expect(roomHue('Bad')).toBe(roomHue('Bad'));
    for (const name of ['Bad', 'Küche', 'Flur', '']) {
      expect(roomHue(name)).toBeGreaterThanOrEqual(0);
      expect(roomHue(name)).toBeLessThan(ROOM_COLORS.hueDegrees);
    }
  });
  it('trennt verschiedene Räume meist in der Farbe', () => {
    const hues = new Set(['Bad', 'Küche', 'Flur', 'Wohnzimmer', 'Keller'].map(roomHue));
    expect(hues.size).toBeGreaterThan(2);
  });
});
