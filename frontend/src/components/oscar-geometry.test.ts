import { describe, expect, it } from 'vitest';

import { OSCAR_VISIBLE_COUNT, oscarCenterIndex } from './oscar-geometry.ts';

describe('oscarCenterIndex', () => {
  it('zentriert die ganze Gruppe, solange alle ins Fenster passen', () => {
    expect(oscarCenterIndex(2, 0)).toBe(0.5);
    expect(oscarCenterIndex(OSCAR_VISIBLE_COUNT, 0)).toBe((OSCAR_VISIBLE_COUNT - 1) * 0.5);
  });

  it('hält bei vielen Personen die hervorgehobene mittig', () => {
    expect(oscarCenterIndex(10, 5)).toBe(5);
    expect(oscarCenterIndex(10, 4)).toBe(4);
  });

  it('lässt am Anfang und Ende keinen Leerraum entstehen', () => {
    const reach = (OSCAR_VISIBLE_COUNT - 1) * 0.5;
    expect(oscarCenterIndex(10, -1)).toBe(reach);
    expect(oscarCenterIndex(10, 0)).toBe(reach);
    expect(oscarCenterIndex(10, 9)).toBe(9 - reach);
  });
});
