import type { Matrix, PersonObject, Standing, TaskObject, WeekRate } from '../api/index.ts';
import { CHART, HEAT_LEVELS, PAIR, PERCENT } from '../constants/index.ts';

export interface BarRow {
  readonly personId: string;
  readonly points: number;
  /** Länge des Balkens und Lage des Strichs für den fairen Anteil, jeweils in Prozent der Breite. */
  readonly pointsPercent: number;
  readonly fairPercent: number;
}

/** Balken je Person; alle teilen sich dieselbe Skala, damit Balken und Strich vergleichbar sind. */
export function barRows(standings: readonly Standing[]): readonly BarRow[] {
  const scale = Math.max(1, ...standings.flatMap((entry) => [entry.points, entry.fair_points]));
  return standings.map((entry) => ({
    personId: entry.person_id,
    points: entry.points,
    pointsPercent: (entry.points / scale) * PERCENT,
    fairPercent: (entry.fair_points / scale) * PERCENT,
  }));
}

export interface ChartPoint {
  readonly x: number;
  /** Leer, wenn in der Woche nichts abgeschlossen wurde. */
  readonly y: number | undefined;
  readonly weekStart: string;
  readonly rate: number | null;
}

/** Punkte des Liniendiagramms: Wochen gleichmäßig verteilt, Quote von 0 (unten) bis 1 (oben). */
export function chartPoints(weeks: readonly WeekRate[]): readonly ChartPoint[] {
  const span = CHART.right - CHART.left;
  const step = weeks.length > 1 ? span / (weeks.length - 1) : 0;
  const offset = weeks.length > 1 ? 0 : span / PAIR;
  return weeks.map((week, index) => ({
    x: CHART.left + offset + step * index,
    y: week.rate === null ? undefined : CHART.bottom - week.rate * (CHART.bottom - CHART.top),
    weekStart: week.week_start,
    rate: week.rate,
  }));
}

/** Zusammenhängende Abschnitte mit Werten; eine Woche ohne Wert unterbricht die Linie. */
export function chartSegments(points: readonly ChartPoint[]): readonly (readonly ChartPoint[])[] {
  const segments: ChartPoint[][] = [];
  let current: ChartPoint[] = [];
  for (const point of points) {
    if (point.y === undefined) {
      current = [];
    } else {
      if (current.length === 0) {
        segments.push(current);
      }
      current.push(point);
    }
  }
  return segments;
}

export interface MatrixCell {
  readonly personId: string;
  /** Leer, wenn die Person die Aufgabe nicht übernehmen darf. */
  readonly count: number | undefined;
  /** Farbstufe von 0 (keine) bis `HEAT_LEVELS`. */
  readonly level: number;
}

export interface MatrixRow {
  readonly taskId: string;
  /** Leer, wenn die Aufgabe gelöscht wurde. */
  readonly name: string | undefined;
  readonly cells: readonly MatrixCell[];
}

/** Zeilen je Aufgabe (auch gelöschte mit Zuteilungen), Spalten je Person. */
export function matrixRows(
  matrix: Matrix,
  tasks: readonly TaskObject[],
  persons: readonly PersonObject[],
): readonly MatrixRow[] {
  const known = new Set(tasks.map((task) => task.id));
  const removed = Object.keys(matrix).filter((id) => !known.has(id));
  const rows = [
    ...tasks.map((task) => ({ taskId: task.id, name: task.name, allowed: new Set(task.allowed) })),
    ...removed.map((taskId) => ({ taskId, name: undefined, allowed: undefined })),
  ];
  const counts = rows.flatMap((row) => persons.map((p) => matrix[row.taskId]?.[p.id] ?? 0));
  const max = Math.max(1, ...counts);
  return rows.map((row) => ({
    taskId: row.taskId,
    name: row.name,
    cells: persons.map((person) => {
      const count = matrix[row.taskId]?.[person.id] ?? 0;
      const permitted = row.allowed === undefined || row.allowed.has(person.id) || count > 0;
      return {
        personId: person.id,
        count: permitted ? count : undefined,
        level: Math.ceil((count / max) * HEAT_LEVELS),
      };
    }),
  }));
}
