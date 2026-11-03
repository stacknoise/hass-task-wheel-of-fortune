import {
  PLINKO_ARC_SHAPE,
  PLINKO_BIN_HEIGHT,
  PLINKO_BIN_MARGIN,
  PLINKO_BIN_MARGIN_SHARE,
  PLINKO_BIN_TOP,
  PLINKO_BOARD_LEFT,
  PLINKO_BOARD_RIGHT,
  PLINKO_EDGE_TOLERANCE,
  PLINKO_END_ARC,
  PLINKO_FIRST_MS,
  PLINKO_FIRST_ROW_Y,
  PLINKO_HALF,
  PLINKO_HIT_OFFSET,
  PLINKO_LANDING_OFFSET,
  PLINKO_LAST_MS,
  PLINKO_PATH_START_Y,
  PLINKO_PEG_ARC,
  PLINKO_PEG_SPACING,
  PLINKO_ROWS,
  PLINKO_ROW_PERIOD,
  PLINKO_ROW_SPACING,
  PLINKO_START_JITTER,
  PLINKO_STEP_MAX_MS,
  PLINKO_STEP_MIN_MS,
} from '../constants/index.ts';
import { numberText } from './format.ts';
import { lerp, randomBetween } from './motion.ts';
import type { Share } from './stage-base.ts';

/** Ein Fach am Boden; es reicht von `x0` bis `x1`, die Breite ist die Chance mal Brettbreite. */
export interface Bin extends Share {
  readonly x0: number;
  readonly x1: number;
}

export type PointKind = 'start' | 'peg' | 'end';

/** Ein Punkt der Kugelbahn; `peg` ist der Schlüssel des getroffenen Stifts (nur bei `kind` „peg“). */
export interface PathPoint {
  readonly x: number;
  readonly y: number;
  readonly kind: PointKind;
  readonly peg: string | undefined;
}

export interface Peg {
  readonly key: string;
  readonly x: number;
  readonly y: number;
}

export interface BallState {
  readonly x: number;
  readonly y: number;
  /** Nummer des Bahnabschnitts, in dem die Kugel gerade ist. */
  readonly segment: number;
}

type Random = () => number;

const HALF_SPACING = PLINKO_PEG_SPACING * PLINKO_HALF;
const BOARD_WIDTH = PLINKO_BOARD_RIGHT - PLINKO_BOARD_LEFT;
const LAST_ROW = PLINKO_ROWS - 1;
const ROW_INDEXES = Array.from({ length: PLINKO_ROWS }, (_unused, row) => row);

/** Wie sich die Kugel in einem Abschnitt bewegt: Fall (0..1) und Bogen (0..1) über den Fortschritt. */
interface Curve {
  readonly fall: (progress: number) => number;
  readonly arc: (progress: number) => number;
  readonly lift: number;
}

const parabola = (progress: number): number => PLINKO_ARC_SHAPE * progress * (1 - progress);
const CURVES: Readonly<Record<PointKind, Curve>> = {
  start: { fall: (progress) => progress * progress, arc: () => 0, lift: 0 },
  peg: { fall: (progress) => progress, arc: parabola, lift: PLINKO_PEG_ARC },
  end: {
    fall: (progress) => progress * progress,
    arc: (progress) => parabola(progress) * (1 - progress),
    lift: PLINKO_END_ARC,
  },
};

export function pegKey(row: number, index: number): string {
  return `${numberText(row)}:${numberText(index)}`;
}

/** Erster Stift, Stiftzahl und letzter Stift der Reihe `row`; ungerade Reihen sind versetzt. */
function rowBounds(row: number): { first: number; count: number; last: number } {
  const first = PLINKO_BOARD_LEFT + HALF_SPACING + (row % PLINKO_ROW_PERIOD) * HALF_SPACING;
  const room = PLINKO_BOARD_RIGHT - HALF_SPACING - first + PLINKO_EDGE_TOLERANCE;
  const count = Math.floor(room / PLINKO_PEG_SPACING) + 1;
  return { first, count, last: first + (count - 1) * PLINKO_PEG_SPACING };
}

const rowY = (row: number): number => PLINKO_FIRST_ROW_Y + row * PLINKO_ROW_SPACING;

/** Alle Stifte des Bretts, Reihe für Reihe. */
export const PEGS: readonly Peg[] = ROW_INDEXES.flatMap((row) => {
  const { first, count } = rowBounds(row);
  return Array.from({ length: count }, (_unused, index) => ({
    key: pegKey(row, index),
    x: first + index * PLINKO_PEG_SPACING,
    y: rowY(row),
  }));
});

/** Legt die Fächer nebeneinander über die Brettbreite. */
export function layoutBins(shares: readonly Share[]): readonly Bin[] {
  let edge = PLINKO_BOARD_LEFT;
  return shares.map((share) => {
    const x0 = edge;
    edge += share.share * BOARD_WIDTH;
    return { ...share, x0, x1: edge };
  });
}

/** Das Fach, in dem die Stelle `x` liegt. */
export function binAt(bins: readonly Bin[], x: number): Bin | undefined {
  return bins.find((bin) => x >= bin.x0 && x < bin.x1);
}

/** Landepunkt im Fach: `fraction` (0..1) verteilt über die Fachbreite, mit Abstand zu den Wänden. */
export function landingPoint(bin: Bin, fraction: number): PathPoint {
  const width = bin.x1 - bin.x0;
  const margin = Math.min(PLINKO_BIN_MARGIN, width * PLINKO_BIN_MARGIN_SHARE);
  return {
    x: bin.x0 + margin + fraction * (width - margin - margin),
    y: PLINKO_BIN_TOP + PLINKO_BIN_HEIGHT - PLINKO_LANDING_OFFSET,
    kind: 'end',
    peg: undefined,
  };
}

/** Der Stift der Reihe `row`, der `x` am nächsten ist (Index in der Reihe). */
function nearestIndex(row: number, x: number): number {
  const { first, count } = rowBounds(row);
  const index = Math.round((x - first) / PLINKO_PEG_SPACING);
  return Math.min(Math.max(index, 0), count - 1);
}

const pegX = (row: number, index: number): number =>
  rowBounds(row).first + index * PLINKO_PEG_SPACING;

/** Ein Schritt rückwärts: der Stift der Reihe darüber, einen halben Abstand links oder rechts. */
function stepBack(row: number, x: number, random: Random): number {
  const { first, last } = rowBounds(row);
  const options = [x - HALF_SPACING, x + HALF_SPACING].filter(
    (candidate) =>
      candidate >= first - PLINKO_EDGE_TOLERANCE && candidate <= last + PLINKO_EDGE_TOLERANCE,
  );
  const pick = Math.min(Math.floor(random() * options.length), options.length - 1);
  return options[pick] ?? x;
}

/** Die Stiftreihen von oben nach unten, rückwärts vom letzten Stift über dem Ziel bestimmt. */
function pegColumns(targetX: number, random: Random): readonly number[] {
  let x = pegX(LAST_ROW, nearestIndex(LAST_ROW, targetX));
  const columns = [x];
  for (let row = LAST_ROW - 1; row >= 0; row--) {
    x = stepBack(row, x, random);
    columns.unshift(x);
  }
  return columns;
}

/**
 * Die Kugelbahn vom Start bis ins Fach `bin`: Der Weg wird rückwärts vom Landepunkt als Zufallsweg
 * über die Stiftreihen berechnet (je Reihe ±halber Stiftabstand), so landet die Kugel immer im Fach.
 */
export function buildPath(bin: Bin, random: Random = Math.random): readonly PathPoint[] {
  const end = landingPoint(bin, random());
  const columns = pegColumns(end.x, random);
  const pegs = columns.map((x, row): PathPoint => {
    return {
      x,
      y: rowY(row) - PLINKO_HIT_OFFSET,
      kind: 'peg',
      peg: pegKey(row, nearestIndex(row, x)),
    };
  });
  const jitter = randomBetween(-PLINKO_START_JITTER, PLINKO_START_JITTER, random);
  const start: PathPoint = {
    x: (columns[0] ?? end.x) + jitter,
    y: PLINKO_PATH_START_Y,
    kind: 'start',
    peg: undefined,
  };
  return [start, ...pegs, end];
}

/** Zeit je Bahnabschnitt in ms: erster und letzter Abschnitt fest, die übrigen leicht zufällig. */
export function stepDurations(
  points: readonly PathPoint[],
  random: Random = Math.random,
): number[] {
  const count = Math.max(points.length - 1, 0);
  const last = count - 1;
  return Array.from({ length: count }, (_unused, index) => {
    if (index === 0) {
      return PLINKO_FIRST_MS;
    }
    return index === last
      ? PLINKO_LAST_MS
      : randomBetween(PLINKO_STEP_MIN_MS, PLINKO_STEP_MAX_MS, random);
  });
}

function interpolate(points: readonly PathPoint[], segment: number, progress: number): BallState {
  const from = points[segment];
  const to = points[segment + 1];
  if (!from || !to) {
    const edge = points.at(-1) ?? { x: 0, y: 0 };
    return { x: edge.x, y: edge.y, segment };
  }
  const curve = CURVES[to.kind];
  const y = lerp(from.y, to.y, curve.fall(progress)) - curve.lift * curve.arc(progress);
  return { x: lerp(from.x, to.x, progress), y, segment };
}

/** Stelle der Kugel `elapsedMs` nach dem Start; nach dem Ende bleibt sie am letzten Punkt. */
export function positionAt(
  points: readonly PathPoint[],
  durations: readonly number[],
  elapsedMs: number,
): BallState {
  let from = 0;
  for (const [segment, duration] of durations.entries()) {
    if (elapsedMs < from + duration) {
      return interpolate(points, segment, (elapsedMs - from) / duration);
    }
    from += duration;
  }
  return interpolate(points, durations.length - 1, 1);
}
