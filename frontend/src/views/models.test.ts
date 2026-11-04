import { describe, expect, it } from 'vitest';

import type { AssignmentObject, RoundHead, ScheduleObject, WeekRate } from '../api/index.ts';
import { buildCsv, csvCell } from './csv.ts';
import { groupByRound, swapTargets, recentActivity, upcomingDraws } from './overview-model.ts';
import { barRows, chartPoints, chartSegments } from './statistics-model.ts';

function schedule(
  id: string,
  taskIds: string[],
  extra: Partial<ScheduleObject> = {},
): ScheduleObject {
  return {
    id,
    name: id,
    task_ids: taskIds,
    enabled: true,
    archived: false,
    next_run: null,
    ...extra,
  };
}

describe('csvCell', () => {
  it('setzt in Anführungszeichen und verdoppelt diese', () => {
    expect(csvCell('sagt "hallo"; ok')).toBe('"sagt ""hallo""; ok"');
  });

  it.each(['=1+1', '+1', '-1', '@SUM(A1)', '\tx', '\rx'])('entschärft Formel %j', (value) => {
    expect(csvCell(value)).toBe(`"'${value}"`);
  });

  it('lässt harmlosen Text unverändert', () => {
    expect(csvCell('Bad putzen')).toBe('"Bad putzen"');
  });
});

describe('buildCsv', () => {
  it('trennt mit Semikolon und Zeilenumbruch und beginnt mit Byte-Order-Mark', () => {
    expect(
      buildCsv([
        ['a', 'b'],
        ['c', '=d'],
      ]),
    ).toBe('﻿"a";"b"\r\n"c";"\'=d"');
  });
});

describe('upcomingDraws', () => {
  it('nimmt aktive Zeitpläne mit Termin, den nächsten zuerst', () => {
    const result = upcomingDraws([
      schedule('b', [], { next_run: '2026-12-01T00:00:00Z' }),
      schedule('a', [], { next_run: '2026-11-01T00:00:00Z' }),
      schedule('off', [], { next_run: '2026-11-01T00:00:00Z', enabled: false }),
      schedule('old', [], { next_run: '2026-11-01T00:00:00Z', archived: true }),
      schedule('manual', []),
    ]);
    expect(result.map((item) => item.id)).toEqual(['a', 'b']);
  });
});

describe('groupByRound', () => {
  const head = (id: string, scheduleId: string, startedAt: string) =>
    ({ id, schedule_id: scheduleId, started_at: startedAt, total: 2, done: 0 }) as RoundHead;

  it('gruppiert nach Auslosung, die jüngste zuerst, und lässt leere Gruppen weg', () => {
    const items = [
      { id: '1', round_id: 'old' },
      { id: '2', round_id: 'new' },
      { id: '3', round_id: 'lost' },
    ] as unknown as AssignmentObject[];
    const groups = groupByRound(
      items,
      [
        head('old', 's1', '2026-10-01T00:00:00Z'),
        head('new', 'gone', '2026-11-01T00:00:00Z'),
        head('empty', 's1', '2026-11-02T00:00:00Z'),
      ],
      [schedule('s1', [])],
    );
    expect(
      groups.map((g) => [g.round?.id, g.schedule?.id, g.assignments.map((a) => a.id)]),
    ).toEqual([
      ['new', undefined, ['2']],
      ['old', 's1', ['1']],
      [undefined, undefined, ['3']],
    ]);
  });
});

describe('recentActivity', () => {
  it('sortiert nach Erledigungszeit oder Rundenbeginn, neueste zuerst', () => {
    const round = (start: string, done: string | null) =>
      ({
        started_at: start,
        assignments: [{ id: start, done_at: done }],
      }) as never;
    const result = recentActivity(
      [round('2026-11-01T00:00:00Z', null), round('2026-10-01T00:00:00Z', '2026-11-05T00:00:00Z')],
      1,
    );
    expect(result.map((item) => item.assignment.id)).toEqual(['2026-10-01T00:00:00Z']);
  });
});

describe('barRows', () => {
  it('skaliert Balken und Strich auf dieselbe Breite', () => {
    const rows = barRows([
      { person_id: 'a', points: 10, fair_points: 5, difference: 5 },
      { person_id: 'b', points: 2, fair_points: 8, difference: -6 },
    ]);
    expect(rows.map((row) => [row.pointsPercent, row.fairPercent])).toEqual([
      [100, 50],
      [20, 80],
    ]);
  });

  it('teilt nicht durch null', () => {
    expect(barRows([{ person_id: 'a', points: 0, fair_points: 0, difference: 0 }])).toEqual([
      { personId: 'a', points: 0, pointsPercent: 0, fairPercent: 0 },
    ]);
  });
});

describe('chartPoints und chartSegments', () => {
  const week = (rate: number | null): WeekRate => ({
    week_start: '2026-11-02',
    done: 0,
    missed: 0,
    rate,
  });

  it('lässt eine Lücke, wo nichts abgeschlossen wurde', () => {
    const points = chartPoints([week(1), week(null), week(0), week(0.5)]);
    expect(points.map((p) => p.y === undefined)).toEqual([false, true, false, false]);
    expect(chartSegments(points).map((segment) => segment.length)).toEqual([1, 2]);
  });

  it('setzt eine einzelne Woche in die Mitte', () => {
    const [point] = chartPoints([week(1)]);
    expect(point?.x).toBe(216);
  });
});

describe('swapTargets', () => {
  const persons = [
    { id: 'p1', load: 'full' },
    { id: 'p2', load: 'full' },
    { id: 'p3', load: 'full' },
    { id: 'p4', load: 'paused' },
    { id: 'p5', load: 'full' },
  ] as never[];
  const bad = { id: 't1', allowed: ['p1', 'p2', 'p3', 'p4'], swap_allowed: true } as never;
  const kitchen = { id: 't2', allowed: [], swap_allowed: true } as never;
  const fixed = { id: 't3', allowed: [], swap_allowed: false } as never;
  const onlyBen = { id: 't4', allowed: ['p2'], swap_allowed: true } as never;
  const tasks = new Map<string, never>([
    ['t1', bad],
    ['t2', kitchen],
    ['t3', fixed],
    ['t4', onlyBen],
  ]);
  const mine = { id: 'a1', round_id: 'r1', person_id: 'p1', task_id: 't1', status: 'open' };
  const open = (id: string, person: string, task: string, due = '2026-11-10') => ({
    id,
    round_id: 'r1',
    person_id: person,
    task_id: task,
    status: 'open',
    due_at: due,
  });

  it('bietet Personen derselben Auslosung mit ihrer offenen Aufgabe an', () => {
    const round = [mine, open('a2', 'p2', 't2'), open('a3', 'p3', 't2')] as never[];
    const targets = swapTargets(mine as never, bad, round, persons, tasks);
    expect(targets.map((target) => [target.person.id, target.task])).toEqual([
      ['p2', kitchen],
      ['p3', kitchen],
    ]);
  });

  it('lässt pausierte, nicht erlaubte und nicht tauschbare Gegenstücke weg', () => {
    const round = [
      mine,
      open('a2', 'p4', 't2'),
      open('a3', 'p5', 't2'),
      open('a4', 'p2', 't3'),
    ] as never[];
    expect(swapTargets(mine as never, bad, round, persons, tasks)).toEqual([]);
    const back = [open('a5', 'p2', 't4')] as never[];
    expect(swapTargets({ ...mine, person_id: 'p3' } as never, bad, back, persons, tasks)).toEqual(
      [],
    );
  });

  it('nimmt nur offene Zuteilungen derselben Runde und nur die mit der frühesten Frist', () => {
    const round = [
      mine,
      { ...open('a2', 'p2', 't2'), status: 'on_time' },
      { ...open('a3', 'p3', 't2'), status: 'swapped' },
      { ...open('a4', 'p2', 't2', '2026-11-12'), round_id: 'r9' },
      open('a5', 'p2', 't4', '2026-11-20'),
      open('a6', 'p2', 't2', '2026-11-11'),
    ] as never[];
    const targets = swapTargets(mine as never, bad, round, persons, tasks);
    expect(targets.map((target) => target.assignment.id)).toEqual(['a6']);
  });
});
