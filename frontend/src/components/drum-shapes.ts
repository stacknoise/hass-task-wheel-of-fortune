import {
  DRUM_CENTER_X,
  DRUM_CENTER_Y,
  DRUM_LEGEND_ROW,
  DRUM_LEGEND_ROWS,
  DRUM_LEGEND_TOP,
  DRUM_LEGEND_WIDTH,
  DRUM_OPENING_FROM,
  DRUM_OPENING_TO,
  DRUM_RADIUS,
  DRUM_RIB_COUNT,
  DRUM_RIB_LENGTH,
  FULL_CIRCLE,
  HALF_CIRCLE,
  PATH_DECIMALS,
} from '../constants/index.ts';

export interface Point {
  readonly x: number;
  readonly y: number;
}

/** Ein Punkt auf der Trommelwand; Winkel in Grad von der x-Achse nach unten. */
export function wallPoint(degrees: number): Point {
  const radians = (degrees * Math.PI) / HALF_CIRCLE;
  return {
    x: DRUM_CENTER_X + DRUM_RADIUS * Math.cos(radians),
    y: DRUM_CENTER_Y + DRUM_RADIUS * Math.sin(radians),
  };
}

function coordinates(point: Point): string {
  return `${point.x.toFixed(PATH_DECIMALS)} ${point.y.toFixed(PATH_DECIMALS)}`;
}

/** Die Trommelwand als Bogen mit der Öffnung zwischen 30 und 60 Grad. */
export function wallPath(): string {
  const radius = String(DRUM_RADIUS);
  return `M${coordinates(wallPoint(DRUM_OPENING_FROM))} A${radius} ${radius} 0 1 1 ${coordinates(wallPoint(DRUM_OPENING_TO))}`;
}

/** Die Rippen der Trommel als ein Pfad von der Mitte nach außen. */
export function ribsPath(): string {
  const centre = `${String(DRUM_CENTER_X)} ${String(DRUM_CENTER_Y)}`;
  return Array.from({ length: DRUM_RIB_COUNT }, (_, index) => {
    const angle = (index * FULL_CIRCLE) / DRUM_RIB_COUNT;
    const radians = (angle * Math.PI) / HALF_CIRCLE;
    const end = {
      x: DRUM_CENTER_X + DRUM_RIB_LENGTH * Math.cos(radians),
      y: DRUM_CENTER_Y + DRUM_RIB_LENGTH * Math.sin(radians),
    };
    return `M${centre} L${coordinates(end)}`;
  }).join(' ');
}

/** Drehung der Trommel in Grad. */
export function degreesOf(angle: number): number {
  return (angle * HALF_CIRCLE) / Math.PI;
}

/** Platz des Legendeneintrags `index` von `count` (Spalten füllen sich zeilenweise von oben). */
export function legendSlot(index: number, count: number): Point {
  const columns = Math.ceil(count / DRUM_LEGEND_ROWS);
  const width = DRUM_LEGEND_WIDTH / Math.max(1, columns);
  return {
    x: Math.floor(index / DRUM_LEGEND_ROWS) * width,
    y: DRUM_LEGEND_TOP + (index % DRUM_LEGEND_ROWS) * DRUM_LEGEND_ROW,
  };
}
