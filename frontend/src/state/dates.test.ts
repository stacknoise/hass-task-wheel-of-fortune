import { describe, expect, it } from 'vitest';

import { dayOf, fromLocalInput, localInput } from './dates.ts';

describe('Datumsfunktionen', () => {
  it('kürzt Zeitpunkte auf den Kalendertag', () => {
    expect(dayOf('2026-11-03T12:00:00+00:00')).toBe('2026-11-03');
  });

  it('wandelt lokale Eingaben in Zeitpunkte mit Zeitzone', () => {
    const iso = fromLocalInput('2026-11-03T18:30');
    expect(iso.endsWith('Z')).toBe(true);
    expect(localInput(iso)).toBe('2026-11-03T18:30');
    expect(fromLocalInput('')).toBe('');
    expect(localInput('kaputt')).toBe('');
  });
});
