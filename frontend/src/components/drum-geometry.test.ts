import { describe, expect, it } from 'vitest';

import {
  DRUM_CENTER_X,
  DRUM_CENTER_Y,
  DRUM_LEGEND_ROWS,
  DRUM_RADIUS,
  DRUM_RADIUS_FACTOR,
  DRUM_TRAY_X,
  DRUM_TRAY_Y,
} from '../constants/index.ts';
import { createBalls, pickBall } from './drum-balls.ts';
import { DRUM_TOTAL_MS, DrumSimulation } from './drum-geometry.ts';
import { degreesOf, legendSlot, ribsPath, wallPath, wallPoint } from './drum-shapes.ts';
import type { Share } from './stage-base.ts';

const SHARES: Share[] = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6, share: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.3, share: 0.3 },
  { id: 'c', label: 'Clara', color: '#137333', chance: 0.1, share: 0.1 },
];

/** Deterministischer Zufall für reproduzierbare Läufe. */
function seeded(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

function run(sim: DrumSimulation): void {
  for (let elapsed = 0; elapsed <= DRUM_TOTAL_MS; elapsed += 16) {
    sim.advance(elapsed, 0.016);
  }
  sim.advance(DRUM_TOTAL_MS, 0.016);
}

describe('Kugeln', () => {
  it('erzeugt drei Kugeln je Person mit Fläche proportional zur Chance', () => {
    const balls = createBalls(SHARES, seeded(1));
    expect(balls).toHaveLength(9);
    const area = (id: string): number => {
      const ball = balls.find((candidate) => candidate.id === id);
      return Math.PI * (ball?.r ?? 0) ** 2;
    };
    expect(area('a') / area('c')).toBeCloseTo(6, 5);
    expect(balls[0]?.r).toBeCloseTo(DRUM_RADIUS_FACTOR * Math.sqrt(60), 5);
    balls.forEach((ball) => {
      expect(Math.hypot(ball.x - DRUM_CENTER_X, ball.y - DRUM_CENTER_Y) + ball.r).toBeLessThan(
        DRUM_RADIUS,
      );
    });
  });

  it('wählt die Kugel der Person nach dem Anteil im Segment', () => {
    const balls = createBalls(SHARES, seeded(2));
    const mine = balls.filter((ball) => ball.id === 'b');
    expect(pickBall(balls, 'b', 0)).toBe(mine[0]);
    expect(pickBall(balls, 'b', 0.5)).toBe(mine[1]);
    expect(pickBall(balls, 'b', 0.999)).toBe(mine[2]);
    expect(pickBall(balls, 'b', 1)).toBe(mine[2]);
    expect(pickBall(balls, 'x', 0.5)).toBeUndefined();
  });
});

describe('Formen', () => {
  it('berechnet Wand, Rippen, Winkel und Legende', () => {
    expect(wallPoint(0).x).toBeCloseTo(DRUM_CENTER_X + DRUM_RADIUS, 5);
    expect(wallPath()).toMatch(/^M[\d. ]+ A140 140 0 1 1 [\d. ]+$/u);
    expect(ribsPath().match(/M/gu)).toHaveLength(6);
    expect(degreesOf(Math.PI)).toBeCloseTo(180, 5);
    expect(legendSlot(0, 3)).toEqual({ x: 0, y: legendSlot(0, 1).y });
    const wide = legendSlot(DRUM_LEGEND_ROWS, DRUM_LEGEND_ROWS + 1);
    expect(wide.x).toBeGreaterThan(0);
    expect(wide.y).toBe(legendSlot(0, 1).y);
    expect(legendSlot(1, 3).y).toBeGreaterThan(legendSlot(0, 3).y);
  });
});

describe('Simulation', () => {
  it('hält nach dem Einschwingen alle Kugeln in der Trommel', () => {
    const sim = new DrumSimulation(SHARES, seeded(3));
    sim.balls.forEach((ball) => {
      expect(Math.hypot(ball.x - DRUM_CENTER_X, ball.y - DRUM_CENTER_Y)).toBeLessThanOrEqual(
        DRUM_RADIUS,
      );
      expect(Number.isFinite(ball.x + ball.y)).toBe(true);
    });
    expect(sim.landedId()).toBeUndefined();
  });

  it.each([
    ['a', 0.1, 1],
    ['b', 0.5, 2],
    ['c', 0.9, 3],
    ['a', 0.99, 4],
  ])(
    'führt die Gewinnerkugel von %s zuverlässig in die Ablage (Zufall %i)',
    (id, fraction, seed) => {
      const sim = new DrumSimulation(SHARES, seeded(seed));
      sim.choose(id, fraction);
      const target = sim.target;
      expect(target?.id).toBe(id);
      run(sim);
      expect(sim.landedId()).toBe(id);
      expect(target?.x).toBeCloseTo(DRUM_TRAY_X, 5);
      expect(target?.y).toBeCloseTo(DRUM_TRAY_Y, 5);
      expect(target?.scale).toBeGreaterThan(1);
      sim.balls.forEach((ball) => {
        expect(Number.isFinite(ball.x + ball.y)).toBe(true);
      });
    },
  );

  it('läuft unabhängig vom Zufall zum selben Ergebnis, auch bei großen Zeitschritten', () => {
    const ids = [5, 6, 7].map((seed) => {
      const sim = new DrumSimulation(SHARES, seeded(seed));
      sim.choose('c', 0.5);
      for (let elapsed = 0; elapsed <= DRUM_TOTAL_MS; elapsed += 500) {
        sim.advance(elapsed, 5);
      }
      sim.advance(DRUM_TOTAL_MS, 5);
      return sim.landedId();
    });
    expect(ids).toEqual(['c', 'c', 'c']);
  });

  it('zeigt mit finish() direkt den Endstand', () => {
    const sim = new DrumSimulation(SHARES, seeded(8));
    sim.choose('b', 0.2);
    sim.angle = 3;
    sim.finish();
    expect(sim.angle).toBe(0);
    expect(sim.landedId()).toBe('b');
  });

  it('überlebt Läufe ohne Gewinnerkugel und ohne Kugeln', () => {
    const none = new DrumSimulation(SHARES, seeded(9));
    none.choose('x', 0.5);
    expect(none.target).toBeUndefined();
    run(none);
    none.finish();
    expect(none.landedId()).toBeUndefined();
    const empty = new DrumSimulation([], seeded(10));
    run(empty);
    expect(empty.balls).toHaveLength(0);
  });

  it('trennt überlappende Kugeln und ignoriert Kugeln außerhalb', () => {
    const sim = new DrumSimulation([SHARES[0] as Share], seeded(11));
    const [first, second] = sim.balls;
    if (!first || !second) {
      throw new Error('Kugeln fehlen');
    }
    first.x = 100;
    first.y = 100;
    second.x = 102;
    second.y = 100;
    first.vx = 50;
    second.vx = -50;
    sim.step(0.001, 0, -1);
    expect(Math.hypot(second.x - first.x, second.y - first.y)).toBeGreaterThan(2);
    second.out = true;
    const before = first.x;
    first.out = false;
    sim.step(0.001, 0, -1);
    expect(first.x).not.toBe(before);
    second.out = false;
    second.x = first.x;
    second.y = first.y;
    sim.step(0.001, 0, -1);
    sim.step(0.001, 0, 0);
    expect(Number.isFinite(second.x)).toBe(true);
  });
});
