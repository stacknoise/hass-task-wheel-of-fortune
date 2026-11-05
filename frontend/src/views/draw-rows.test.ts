import { describe, expect, it } from 'vitest';

import type { TaskDrawWire } from '../api/index.ts';
import { DRAW_PHASE } from '../constants/index.ts';
import type { DrawState, PersonInfo } from '../state/index.ts';
import { waitingPersons } from './draw-rows.ts';

const PERSONS = new Map<string, PersonInfo>([
  ['a', { id: 'a', name: 'Anna', color: '#c05600' }],
  ['b', { id: 'b', name: 'Ben', color: '#1a5fd0' }],
  ['c', { id: 'c', name: 'Clara', color: '#137333' }],
]);
const result = (winner: string | null): TaskDrawWire => ({
  task_id: 't',
  winner_id: winner,
  chance: 0.5,
  segments: [],
  exclusions: [],
});
const state = (results: TaskDrawWire[], current?: TaskDrawWire): DrawState =>
  ({ phase: DRAW_PHASE.ready, results, current }) as unknown as DrawState;
const names = (rows: readonly PersonInfo[]): string[] => rows.map((person) => person.name);

describe('waitingPersons', () => {
  it('zeigt alle Personen der Runde, solange niemand eine Aufgabe hat', () => {
    expect(names(waitingPersons(state([]), PERSONS))).toEqual(['Anna', 'Ben', 'Clara']);
  });

  it('entfernt Personen, die schon eine Aufgabe haben', () => {
    expect(names(waitingPersons(state([result('b')]), PERSONS))).toEqual(['Anna', 'Clara']);
  });

  it('lässt den Gewinner des laufenden Drehs noch im Rad', () => {
    const current = result('b');
    expect(names(waitingPersons(state([result('a'), current], current), PERSONS))).toEqual([
      'Ben',
      'Clara',
    ]);
  });

  it('ignoriert nicht vergebene Aufgaben', () => {
    expect(names(waitingPersons(state([result(null)]), PERSONS))).toHaveLength(3);
  });
});
