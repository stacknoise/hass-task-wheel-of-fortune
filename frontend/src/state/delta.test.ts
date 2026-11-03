import { describe, expect, it } from 'vitest';

import { EMPTY_SNAPSHOT } from '../api/fake-hass.testing.ts';
import { applyCollectionDelta, applyDelta } from './delta.ts';

describe('applyCollectionDelta', () => {
  it('ersetzt, ergänzt und entfernt nach Kennung', () => {
    const items = [{ id: 'a', n: 1 }, { id: 'b' }];
    const result = applyCollectionDelta(items, {
      upsert: [{ id: 'a', n: 2 }, { id: 'c' }],
      remove: ['b'],
    });
    expect(result).toEqual([{ id: 'a', n: 2 }, { id: 'c' }]);
  });
});

describe('applyDelta', () => {
  it('ändert nur genannte Sammlungen und lässt den Rest unverändert', () => {
    const next = applyDelta(EMPTY_SNAPSHOT, { tasks: { upsert: [{ id: 't2' }], remove: [] } });
    expect(next.tasks).toHaveLength(2);
    expect(next.persons).toBe(EMPTY_SNAPSHOT.persons);
  });

  it('übernimmt neue Einstellungen', () => {
    const next = applyDelta(EMPTY_SNAPSHOT, { settings: { jokers_per_month: 3 } });
    expect(next.settings).toEqual({ jokers_per_month: 3 });
  });
});
