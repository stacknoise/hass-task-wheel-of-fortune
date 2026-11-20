import { describe, expect, it } from 'vitest';

import { EMPTY_SNAPSHOT } from '../api/fake-hass.testing.ts';
import type { Snapshot } from '../api/index.ts';
import {
  allowsPerson,
  drawableSchedules,
  openRoundFor,
  participantsOf,
  personsById,
  taskUsage,
  tasksById,
} from './lookup.ts';

const SNAPSHOT: Snapshot = {
  ...EMPTY_SNAPSHOT,
  persons: [{ id: 'p1', name: 'Anna', color: '#c05600' }, { id: 'p2' }],
  tasks: [{ id: 't1', name: 'Bad', points: 3, allowed: ['p1', 7] }, { id: 't2' }],
  schedules: [
    { id: 's1', name: 'Woche', archived: false, next_run: '2026-11-09T18:00:00Z', next_period: 2 },
    { id: 's2', name: 'Alt', archived: true },
  ],
  panel_rounds: [{ id: 'r1', schedule_id: 's1' }],
};

describe('taskUsage', () => {
  it('nennt die Zeitpläne, in denen die Aufgabe vorkommt, mit ihrem Eintrag', () => {
    const snapshot: Snapshot = {
      ...EMPTY_SNAPSHOT,
      schedules: [
        { id: 's1', name: 'Woche', entries: [{ task_id: 't1', mode: 'min_count', min_count: 2 }] },
        { id: 's2', name: 'Monat', entries: [{ task_id: 't1', mode: 'every_draw', min_count: 1 }] },
        { id: 's3', name: 'Leer', entries: [{ task_id: 't9', mode: 'min_count', min_count: 1 }] },
      ],
    };
    expect(taskUsage(snapshot, 't1')).toEqual([
      {
        scheduleId: 's1',
        scheduleName: 'Woche',
        entry: { task_id: 't1', mode: 'min_count', min_count: 2 },
      },
      {
        scheduleId: 's2',
        scheduleName: 'Monat',
        entry: { task_id: 't1', mode: 'every_draw', min_count: 1 },
      },
    ]);
    expect(taskUsage(snapshot, 'tx')).toEqual([]);
  });
});

describe('lookup', () => {
  it('erlaubt ohne erlaubte Personen jede Person', () => {
    expect(allowsPerson(new Set(), 'p9')).toBe(true);
    expect(allowsPerson(new Set(['p1']), 'p1')).toBe(true);
    expect(allowsPerson(new Set(['p1']), 'p2')).toBe(false);
  });

  it('zählt nur die Personen zur Runde, die das Backend als Teilnehmer nennt', () => {
    const persons = personsById(SNAPSHOT);
    expect([...participantsOf(persons, ['p1']).keys()]).toEqual(['p1']);
    expect([...participantsOf(persons, ['p1', 'p2']).keys()]).toEqual(['p1', 'p2']);
    expect([...participantsOf(persons, []).keys()]).toEqual(['p1', 'p2']);
  });

  it('liest Personen mit Rückfallwerten', () => {
    const persons = personsById(SNAPSHOT);
    expect(persons.get('p1')).toEqual({ id: 'p1', name: 'Anna', color: '#c05600' });
    expect(persons.get('p2')).toMatchObject({ name: 'p2', color: '#727272' });
  });

  it('liest Aufgaben und ignoriert fremde Werte in der Liste der erlaubten Personen', () => {
    const tasks = tasksById(SNAPSHOT);
    expect(tasks.get('t1')).toMatchObject({ name: 'Bad', points: 3 });
    expect([...(tasks.get('t1')?.allowed ?? [])]).toEqual(['p1']);
    expect(tasks.get('t2')).toMatchObject({ points: 0 });
  });

  it('bietet nur nicht archivierte Zeitpläne an', () => {
    expect(drawableSchedules(SNAPSHOT).map((item) => item.id)).toEqual(['s1']);
    expect(drawableSchedules(SNAPSHOT)[0]).toMatchObject({
      nextRun: '2026-11-09T18:00:00Z',
      nextPeriod: 2,
    });
  });

  it('findet die offene Runde eines Zeitplans', () => {
    expect(openRoundFor(SNAPSHOT, 's1')?.id).toBe('r1');
    expect(openRoundFor(SNAPSHOT, 's2')).toBeUndefined();
  });
});
