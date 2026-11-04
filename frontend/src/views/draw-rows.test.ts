import { describe, expect, it } from 'vitest';

import type { TaskDrawWire } from '../api/index.ts';
import { CHANCE_FREE_ANIMATIONS } from '../constants/index.ts';
import type { PersonInfo, TaskInfo } from '../state/index.ts';
import { personRows } from './draw-rows.ts';

const PERSONS = new Map<string, PersonInfo>([
  ['a', { id: 'a', name: 'Anna', color: '#c05600' }],
  ['b', { id: 'b', name: 'Ben', color: '#1a5fd0' }],
]);
const TASK: TaskInfo = {
  id: 't',
  name: 'Bad',
  points: 1,
  dueDays: 1,
  allowed: new Set<string>(),
  areaId: '',
};
const RESULT: TaskDrawWire = {
  task_id: 't',
  winner_id: null,
  chance: 0,
  segments: [{ person_id: 'a', chance: 0.6, weight: 1 }],
  exclusions: [{ person_id: 'b', reason: 'absent' }],
};
const text = (key: string): string => key;

describe('personRows', () => {
  it('zeigt die Chance und den Ausschlussgrund', () => {
    const [anna, ben] = personRows(RESULT, TASK, PERSONS, true, text);
    expect(anna?.note).toBe('60 %');
    expect(ben?.note).toBe('draw.reason.absent');
  });

  it('lässt die Chance bei Animationen ohne Chance-Anzeige weg', () => {
    expect(CHANCE_FREE_ANIMATIONS).toContain('scratch');
    const [anna, ben] = personRows(RESULT, TASK, PERSONS, false, text);
    expect(anna?.note).toBe('');
    expect(anna?.inWheel).toBe(true);
    expect(ben?.note).toBe('draw.reason.absent');
  });
});
