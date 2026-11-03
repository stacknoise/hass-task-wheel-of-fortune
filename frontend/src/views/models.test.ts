import { describe, expect, it } from 'vitest';

import type { AssignmentObject, ScheduleObject, WeekRate } from '../api/index.ts';
import { buildCsv, csvCell } from './csv.ts';
import { groupBySchedule, recentActivity, upcomingDraws } from './overview-model.ts';
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

describe('groupBySchedule', () => {
  it('ordnet jede Zuteilung dem ersten Zeitplan mit ihrer Aufgabe zu und lässt leere Gruppen weg', () => {
    const items = [
      { id: '1', task_id: 'x' },
      { id: '2', task_id: 'y' },
      { id: '3', task_id: 'z' },
    ] as unknown as AssignmentObject[];
    const groups = groupBySchedule(items, [
      schedule('s1', ['x']),
      schedule('s2', ['x', 'y']),
      schedule('s3', []),
    ]);
    expect(groups.map((g) => [g.schedule?.id, g.assignments.map((a) => a.id)])).toEqual([
      ['s1', ['1']],
      ['s2', ['2']],
      [undefined, ['3']],
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
