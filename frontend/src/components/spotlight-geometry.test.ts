import { describe, expect, it } from 'vitest';

import { SPOTLIGHT_MIN_DELAY_MS, SPOTLIGHT_STEPS } from '../constants/index.ts';
import { layoutTiles, spotlightDelay, spotlightSequence } from './spotlight-geometry.ts';
import type { Rect } from './spotlight-geometry.ts';
import { sharesOf } from './stage-base.ts';

const RECT: Rect = { x: 0, y: 0, w: 4, h: 3 };

function segments(chances: number[]) {
  return chances.map((chance, index) => ({
    id: `s${String(index)}`,
    label: `P${String(index)}`,
    color: '#123456',
    chance,
  }));
}

function seeded(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

describe('layoutTiles', () => {
  it.each([[[1]], [[1, 1]], [[0.5, 0.3, 0.1, 0.07, 0.03]], [[0.9, 0.05, 0.05]]])(
    'Flächen sind proportional zur Chance und füllen alles (%j)',
    (chances) => {
      const shares = sharesOf(segments(chances));
      const tiles = layoutTiles(shares, RECT);
      expect(tiles).toHaveLength(chances.length);
      const total = RECT.w * RECT.h;
      expect(tiles.reduce((sum, tile) => sum + tile.w * tile.h, 0)).toBeCloseTo(total);
      for (const tile of tiles) {
        expect((tile.w * tile.h) / total).toBeCloseTo(tile.share);
        expect(tile.x).toBeGreaterThanOrEqual(0);
        expect(tile.y).toBeGreaterThanOrEqual(0);
        expect(tile.x + tile.w).toBeLessThanOrEqual(RECT.w + 1e-9);
        expect(tile.y + tile.h).toBeLessThanOrEqual(RECT.h + 1e-9);
      }
    },
  );

  it('eine Kachel füllt das ganze Rechteck, keine Kacheln ergeben nichts', () => {
    const [only] = layoutTiles(sharesOf(segments([2])), RECT);
    expect(only).toMatchObject(RECT);
    expect(layoutTiles([], RECT)).toEqual([]);
  });

  it('teilt breite Flächen nebeneinander und hohe übereinander', () => {
    const wide = layoutTiles(sharesOf(segments([1, 1])), RECT);
    expect(wide.map((tile) => tile.x)).toEqual([0, 2]);
    const tall = layoutTiles(sharesOf(segments([1, 1])), { x: 0, y: 0, w: 1, h: 2 });
    expect(tall.map((tile) => tile.y)).toEqual([0, 1]);
  });

  it('überlappt nicht', () => {
    const tiles = layoutTiles(sharesOf(segments([5, 4, 3, 2, 1])), RECT);
    for (const a of tiles) {
      for (const b of tiles) {
        if (a === b) {
          continue;
        }
        const overlapX = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
        const overlapY = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
        expect(overlapX > 1e-9 && overlapY > 1e-9).toBe(false);
      }
    }
  });
});

describe('spotlightSequence', () => {
  const ids = ['a', 'b', 'c'];

  it.each([1, 2, 3, 4])(
    'endet beim Gewinner und wiederholt nie hintereinander (Zufall %i)',
    (seed) => {
      const sequence = spotlightSequence(ids, 'b', seeded(seed));
      expect(sequence).toHaveLength(SPOTLIGHT_STEPS);
      expect(sequence.at(-1)).toBe('b');
      sequence.slice(1).forEach((id, index) => {
        expect(id).not.toBe(sequence[index]);
      });
    },
  );

  it('übersteht Grenzwerte des Zufalls', () => {
    expect(spotlightSequence(ids, 'a', () => 0).at(-1)).toBe('a');
    expect(spotlightSequence(ids, 'a', () => 0.999999).at(-1)).toBe('a');
    expect(spotlightSequence(ids, 'a', () => 1).at(-1)).toBe('a');
  });

  it('bleibt bei einer Kachel auf ihr', () => {
    expect(new Set(spotlightSequence(['a'], 'a', Math.random, 5))).toEqual(new Set(['a']));
  });

  it('bleibt ohne Kacheln beim Gewinner', () => {
    expect(spotlightSequence([], 'a', Math.random, 3)).toEqual(['a', 'a', 'a']);
  });
});

describe('spotlightDelay', () => {
  it('wächst kubisch von der Mindestdauer an', () => {
    expect(spotlightDelay(0, 10)).toBe(SPOTLIGHT_MIN_DELAY_MS);
    const delays = Array.from({ length: 10 }, (_, index) => spotlightDelay(index, 10));
    delays.slice(1).forEach((delay, index) => {
      expect(delay).toBeGreaterThan(delays[index] ?? Infinity);
    });
    const early = spotlightDelay(1, 10) - spotlightDelay(0, 10);
    const late = spotlightDelay(9, 10) - spotlightDelay(8, 10);
    expect(late).toBeGreaterThan(early * 10);
  });

  it('kommt mit einem Sprung aus', () => {
    expect(Number.isFinite(spotlightDelay(0, 1))).toBe(true);
  });
});
