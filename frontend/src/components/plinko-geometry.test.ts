import { describe, expect, it } from 'vitest';

import {
  PLINKO_BOARD_LEFT,
  PLINKO_BOARD_RIGHT,
  PLINKO_FIRST_MS,
  PLINKO_LAST_MS,
  PLINKO_PEG_SPACING,
  PLINKO_ROWS,
} from '../constants/index.ts';
import {
  PEGS,
  binAt,
  buildPath,
  landingPoint,
  layoutBins,
  pegKey,
  positionAt,
  stepDurations,
} from './plinko-geometry.ts';
import { sharesOf } from './stage-base.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.38 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.02 },
];
const BINS = layoutBins(sharesOf(SEGMENTS));
const RANDOMS = [0, 0.25, 0.5, 0.75, 0.999999];

function sequence(values: readonly number[]): () => number {
  let index = 0;
  return () => values[index++ % values.length] ?? 0;
}

describe('plinko-geometry', () => {
  it('legt Fächer proportional zur Chance über die Brettbreite', () => {
    expect(BINS).toHaveLength(3);
    expect(BINS[0]?.x0).toBe(PLINKO_BOARD_LEFT);
    expect(BINS[2]?.x1).toBeCloseTo(PLINKO_BOARD_RIGHT);
    const widths = BINS.map((bin) => bin.x1 - bin.x0);
    expect((widths[0] ?? 0) / (widths[1] ?? 1)).toBeCloseTo(0.6 / 0.38);
    expect(layoutBins([])).toEqual([]);
  });

  it('findet das Fach zu einer Stelle', () => {
    expect(binAt(BINS, 20)?.id).toBe('a');
    expect(binAt(BINS, BINS[1]?.x0 ?? 0)?.id).toBe('b');
    expect(binAt(BINS, 5)).toBeUndefined();
    expect(binAt([], 200)).toBeUndefined();
  });

  it('hat versetzte Stiftreihen innerhalb des Bretts', () => {
    expect(new Set(PEGS.map((peg) => peg.key)).size).toBe(PEGS.length);
    for (const peg of PEGS) {
      expect(peg.x).toBeGreaterThan(PLINKO_BOARD_LEFT);
      expect(peg.x).toBeLessThan(PLINKO_BOARD_RIGHT);
    }
    expect(PEGS[0]?.key).toBe(pegKey(0, 0));
  });

  it('landet immer im Fach des Gewinners, auch bei schmalen Fächern und Randwerten', () => {
    for (const bin of BINS) {
      for (const random of RANDOMS) {
        const end = landingPoint(bin, random);
        expect(binAt(BINS, end.x)?.id).toBe(bin.id);
        const path = buildPath(bin, sequence([random, 1 - random, 0.5]));
        const last = path.at(-1);
        expect(last?.kind).toBe('end');
        expect(binAt(BINS, last?.x ?? 0)?.id).toBe(bin.id);
      }
    }
  });

  it('läuft zwischen den Stiftreihen: Schritte von halbem Stiftabstand, innerhalb des Bretts', () => {
    for (const bin of BINS) {
      for (let seed = 0; seed < RANDOMS.length; seed++) {
        const path = buildPath(bin, sequence([...RANDOMS.slice(seed), ...RANDOMS.slice(0, seed)]));
        const pegs = path.filter((point) => point.kind === 'peg');
        expect(pegs).toHaveLength(PLINKO_ROWS);
        pegs.slice(1).forEach((point, row) => {
          expect(Math.abs(point.x - (pegs[row]?.x ?? 0))).toBeCloseTo(PLINKO_PEG_SPACING / 2);
          expect(point.y).toBeGreaterThan(pegs[row]?.y ?? 0);
        });
        pegs.forEach((point) => {
          expect(PEGS.some((peg) => peg.key === point.peg && peg.x === point.x)).toBe(true);
        });
        for (const point of path) {
          expect(point.x).toBeGreaterThan(PLINKO_BOARD_LEFT);
          expect(point.x).toBeLessThan(PLINKO_BOARD_RIGHT);
        }
      }
    }
  });

  it('funktioniert mit Standard-Zufall und einem einzigen Fach', () => {
    const [only] = layoutBins(sharesOf([{ id: 'x', label: 'X', color: '', chance: 1 }]));
    expect(only).toBeDefined();
    if (only) {
      const path = buildPath(only);
      expect(binAt([only], path.at(-1)?.x ?? 0)?.id).toBe('x');
    }
  });

  it('teilt die Bahn in Abschnitte und führt die Kugel von Start zu Ende', () => {
    const [bin] = BINS;
    expect(bin).toBeDefined();
    if (!bin) {
      return;
    }
    const path = buildPath(bin, sequence(RANDOMS));
    const durations = stepDurations(path, sequence(RANDOMS));
    expect(durations).toHaveLength(path.length - 1);
    expect(durations[0]).toBe(PLINKO_FIRST_MS);
    expect(durations.at(-1)).toBe(PLINKO_LAST_MS);
    expect(stepDurations([])).toEqual([]);
    const total = durations.reduce((sum, duration) => sum + duration, 0);
    const start = positionAt(path, durations, 0);
    expect(start.segment).toBe(0);
    expect(start.x).toBeCloseTo(path[0]?.x ?? 0);
    const mid = positionAt(path, durations, durations[0] ?? 0);
    expect(mid.segment).toBe(1);
    const end = positionAt(path, durations, total + 1000);
    expect(end.x).toBeCloseTo(path.at(-1)?.x ?? 0);
    expect(end.y).toBeCloseTo(path.at(-1)?.y ?? 0);
    expect(positionAt([], [], 0)).toEqual({ x: 0, y: 0, segment: -1 });
  });
});
