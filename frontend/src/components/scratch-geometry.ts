import {
  SCRATCH_ALPHA_OFFSET,
  SCRATCH_CANVAS_HEIGHT,
  SCRATCH_CANVAS_WIDTH,
  SCRATCH_CHANNELS,
  SCRATCH_CLEAR_ALPHA,
  SCRATCH_COIN_MARGIN,
  SCRATCH_COIN_ROWS,
  SCRATCH_COIN_ROW_STEP,
  SCRATCH_COIN_TRAIL,
  SCRATCH_COIN_WOBBLE,
  SCRATCH_COIN_WOBBLE_FREQUENCY,
  SCRATCH_PAIR,
  SCRATCH_SAMPLE_STEP,
} from '../constants/index.ts';

export interface Point {
  readonly x: number;
  readonly y: number;
}

/** Anteil (0..1) der Stichprobe, die frei gerubbelt ist; `rgba` sind die Bildpunkte als Folge R, G, B, A. */
export function clearedShare(rgba: ArrayLike<number>): number {
  const stride = SCRATCH_CHANNELS * SCRATCH_SAMPLE_STEP;
  let total = 0;
  let cleared = 0;
  for (let index = SCRATCH_ALPHA_OFFSET; index < rgba.length; index += stride) {
    total += 1;
    if ((rgba[index] ?? 0) < SCRATCH_CLEAR_ALPHA) {
      cleared += 1;
    }
  }
  return total > 0 ? cleared / total : 0;
}

/** Ein Punkt in Zeichenflächen-Einheiten aus einer Position auf der (skalierten) Karte. */
export function toCanvas(
  client: Point,
  box: {
    readonly left: number;
    readonly top: number;
    readonly width: number;
    readonly height: number;
  },
): Point {
  return {
    x: ((client.x - box.left) / box.width) * SCRATCH_CANVAS_WIDTH,
    y: ((client.y - box.top) / box.height) * SCRATCH_CANVAS_HEIGHT,
  };
}

/**
 * Der Strich der Münze bei `progress` (0..1): sie läuft in Reihen im Zickzack über das Los,
 * jede Reihe in die Gegenrichtung der vorigen.
 */
export function coinStroke(progress: number): { readonly from: Point; readonly to: Point } {
  const scaled = progress * SCRATCH_COIN_ROWS;
  const row = Math.min(SCRATCH_COIN_ROWS - 1, Math.floor(scaled));
  const fraction = scaled - row;
  const span = SCRATCH_CANVAS_WIDTH - SCRATCH_PAIR * SCRATCH_COIN_MARGIN;
  const x = (at: number): number =>
    SCRATCH_COIN_MARGIN + (row % SCRATCH_PAIR === 1 ? 1 - at : at) * span;
  const y = SCRATCH_COIN_MARGIN + row * SCRATCH_COIN_ROW_STEP;
  return {
    from: { x: x(Math.max(0, fraction - SCRATCH_COIN_TRAIL)), y },
    to: {
      x: x(fraction),
      y: y + Math.sin(fraction * SCRATCH_COIN_WOBBLE_FREQUENCY) * SCRATCH_COIN_WOBBLE,
    },
  };
}
