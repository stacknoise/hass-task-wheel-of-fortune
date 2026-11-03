import { describe, expect, it } from 'vitest';

import { SLOT_CYCLE_HEIGHT } from '../constants/index.ts';
import {
  brakeProgress,
  cellIndexAt,
  layoutCells,
  rebase,
  recoilPosition,
  startPosition,
  stripOffset,
  targetPosition,
} from './slot-geometry.ts';
import type { SlotCell } from './slot-geometry.ts';

const shares = [
  { id: 'a', label: 'Anna', color: '#111', chance: 6, share: 0.6 },
  { id: 'b', label: 'Ben', color: '#222', chance: 3, share: 0.3 },
  { id: 'c', label: 'Clara', color: '#333', chance: 1, share: 0.1 },
];
const cells = layoutCells(shares);
const FRACTIONS = [0, 0.001, 0.25, 0.5, 0.75, 0.999, 1];

describe('slot-geometry', () => {
  it('legt Zeilen lückenlos mit Höhe proportional zur Chance', () => {
    expect(cells.map((cell) => cell.height)).toEqual([
      0.6 * SLOT_CYCLE_HEIGHT,
      0.3 * SLOT_CYCLE_HEIGHT,
      0.1 * SLOT_CYCLE_HEIGHT,
    ]);
    expect(cells[1]?.top).toBeCloseTo(cells[0]?.height ?? 0);
    expect(layoutCells([])).toEqual([]);
  });

  it('Zielposition liegt für jede Person und jeden Anteil im richtigen Segment', () => {
    cells.forEach((cell, index) => {
      FRACTIONS.forEach((fraction) => {
        const position = targetPosition(cell, fraction);
        expect(cellIndexAt(cells, position)).toBe(index);
        expect(position).toBeGreaterThanOrEqual(position - cell.height);
      });
    });
  });

  it('findet die Zeile unter der Linie auch bei Rand, negativen und großen Werten', () => {
    expect(cellIndexAt(cells, 0)).toBe(0);
    expect(cellIndexAt(cells, -1)).toBe(2);
    expect(cellIndexAt(cells, SLOT_CYCLE_HEIGHT * 5 + 1)).toBe(0);
    expect(cellIndexAt(cells, SLOT_CYCLE_HEIGHT * 2 - 0.0000001)).toBe(2);
    expect(cellIndexAt([], 10)).toBe(-1);
  });

  it('setzt auf den Startumlauf zurück, ohne den Anblick zu ändern', () => {
    const position = targetPosition(cells[1] as SlotCell, 0.5);
    const base = rebase(position);
    expect(base).toBeLessThan(position);
    expect(cellIndexAt(cells, base)).toBe(1);
    expect(cellIndexAt(cells, startPosition())).toBe(0);
    expect(rebase(-1)).toBeGreaterThan(0);
  });

  it('berechnet Verschiebung, Zurückziehen und Bremsen', () => {
    expect(stripOffset(100, 200)).toBe(0);
    expect(recoilPosition(500, 0)).toBe(500);
    expect(recoilPosition(500, 1)).toBeLessThan(500);
    expect(brakeProgress(0)).toBe(0);
    expect(brakeProgress(1)).toBe(1);
    expect(brakeProgress(0.5)).toBeGreaterThan(0.5);
  });
});
