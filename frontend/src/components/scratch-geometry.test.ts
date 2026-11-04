import { describe, expect, it } from 'vitest';

import {
  SCRATCH_ALPHA_OFFSET,
  SCRATCH_CANVAS_HEIGHT,
  SCRATCH_CANVAS_WIDTH,
  SCRATCH_CHANNELS,
  SCRATCH_COIN_ROWS,
  SCRATCH_SAMPLE_STEP,
} from '../constants/index.ts';
import { clearedShare, coinStroke, toCanvas } from './scratch-geometry.ts';

const SIZE = SCRATCH_CHANNELS * SCRATCH_SAMPLE_STEP * 10;

function pixels(alpha: number): Uint8ClampedArray {
  const data = new Uint8ClampedArray(SIZE);
  for (let index = SCRATCH_ALPHA_OFFSET; index < SIZE; index += SCRATCH_CHANNELS) {
    data[index] = alpha;
  }
  return data;
}

describe('clearedShare', () => {
  it('misst den Anteil durchsichtiger Bildpunkte', () => {
    expect(clearedShare(pixels(255))).toBe(0);
    expect(clearedShare(pixels(0))).toBe(1);
    expect(clearedShare(new Uint8ClampedArray(0))).toBe(0);
  });

  it('zählt nur die Stichprobe', () => {
    const data = pixels(255);
    data[SCRATCH_ALPHA_OFFSET] = 0;
    expect(clearedShare(data)).toBeGreaterThan(0);
    expect(clearedShare(data)).toBeLessThan(1);
  });
});

describe('toCanvas', () => {
  it('rechnet Bildschirm- in Zeichenflächen-Einheiten um', () => {
    const box = { left: 10, top: 20, width: 160, height: 110 };
    expect(toCanvas({ x: 90, y: 75 }, box)).toEqual({
      x: SCRATCH_CANVAS_WIDTH / 2,
      y: SCRATCH_CANVAS_HEIGHT / 2,
    });
  });
});

describe('coinStroke', () => {
  it('läuft in Reihen, jede in die Gegenrichtung der vorigen', () => {
    const first = coinStroke(0.01);
    const second = coinStroke(1 / SCRATCH_COIN_ROWS + 0.01);
    expect(first.to.x).toBeGreaterThan(first.from.x - 1);
    expect(second.to.x).toBeLessThan(second.from.x + 1);
    expect(second.to.y).toBeGreaterThan(first.to.y);
  });

  it('bleibt auch am Ende in der Fläche', () => {
    const last = coinStroke(1);
    expect(last.to.x).toBeGreaterThanOrEqual(0);
    expect(last.to.x).toBeLessThanOrEqual(SCRATCH_CANVAS_WIDTH);
    expect(last.to.y).toBeLessThanOrEqual(SCRATCH_CANVAS_HEIGHT);
  });
});
