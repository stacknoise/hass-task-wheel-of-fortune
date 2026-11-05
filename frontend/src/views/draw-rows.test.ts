import { describe, expect, it } from 'vitest';

import type { TaskDrawWire } from '../api/index.ts';
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
  allowed: new Set<string>(),
  areaIds: [],
};
const RESULT: TaskDrawWire = {
  task_id: 't',
  winner_id: null,
  chance: 0,
  segments: [{ person_id: 'a', chance: 0.6, weight: 1 }],
  exclusions: [{ person_id: 'b', reason: 'absent' }],
};
const LANGUAGE = 'de';

describe('personRows', () => {
  it('zeigt keine Chance, aber den Ausschlussgrund', () => {
    const [anna, ben] = personRows(RESULT, TASK, PERSONS, LANGUAGE);
    expect(anna?.note).toBe('');
    expect(anna?.inWheel).toBe(true);
    expect(ben?.note).toBe('Abwesend');
  });
});
