import { describe, expect, it } from 'vitest';

import { INTERVAL_DEFAULT, defaultStart, newEntry } from './factories.ts';

describe('Standardwerte eines Zeitplans', () => {
  it('beginnt mit der nächsten vollen Stunde nach jetzt', () => {
    expect(defaultStart('2026-11-03T12:20:00+00:00')).toBe('2026-11-03T14:00:00.000Z');
    expect(defaultStart('2026-11-03T12:00:00+00:00')).toBe('2026-11-03T13:00:00.000Z');
  });

  it('nimmt eine neue Aufgabe einmal je Lauf auf und lost wöchentlich', () => {
    expect(newEntry('t1')).toEqual({ task_id: 't1', mode: 'min_count', min_count: 1 });
    expect(INTERVAL_DEFAULT).toEqual({ unit: 'day', every: 7 });
  });
});
