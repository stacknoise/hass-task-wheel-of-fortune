import { describe, expect, it } from 'vitest';

import { decoysOf } from './decoys.ts';

describe('decoysOf', () => {
  it('wählt nie den Gewinner und jede Id höchstens einmal', () => {
    const picked = decoysOf(['a', 'b', 'c', 'd'], 'b', 2, () => 0);
    expect(picked).toEqual(['a', 'c']);
    expect(new Set(picked).size).toBe(picked.length);
  });

  it('nimmt weniger, wenn es nicht genug andere gibt', () => {
    expect(decoysOf(['a', 'b'], 'a', 3, () => 0.99)).toEqual(['b']);
    expect(decoysOf(['a'], 'a', 2, () => 0)).toEqual([]);
  });

  it('folgt dem Zufall', () => {
    expect(decoysOf(['a', 'b', 'c'], 'x', 1, () => 0.99)).toEqual(['c']);
  });
});
