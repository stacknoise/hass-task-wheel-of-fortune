import {
  SPOTLIGHT_SPLIT_AT,
  SPOTLIGHT_DELAY_POWER,
  SPOTLIGHT_DELAY_SPAN_MS,
  SPOTLIGHT_MIN_DELAY_MS,
  SPOTLIGHT_STEPS,
} from '../constants/index.ts';
import { lerp } from './motion.ts';
import type { Share } from './stage-base.ts';

export type Random = () => number;

export interface Rect {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

/** Eine Kachel der Treemap: Person mit Chance und ihrem Rechteck. */
export interface Tile extends Share, Rect {}

const sumOf = (shares: readonly Share[]): number =>
  shares.reduce((sum, share) => sum + share.share, 0);

/** Wo die Liste geteilt wird, damit beide Hälften möglichst gleich viel Chance tragen. */
function splitIndex(shares: readonly Share[]): number {
  const half = sumOf(shares) * SPOTLIGHT_SPLIT_AT;
  let accumulated = 0;
  let best = Number.POSITIVE_INFINITY;
  let split = 1;
  for (const [index, share] of shares.slice(0, -1).entries()) {
    accumulated += share.share;
    const distance = Math.abs(accumulated - half);
    if (distance < best) {
      best = distance;
      split = index + 1;
    }
  }
  return split;
}

/**
 * Treemap: teilt `rect` rekursiv entlang der längeren Seite, sodass die Fläche jeder Kachel
 * proportional zu ihrer Chance ist und alle Kacheln zusammen genau `rect` füllen.
 */
export function layoutTiles(shares: readonly Share[], rect: Rect): Tile[] {
  if (shares.length <= 1) {
    return shares.map((share) => ({ ...share, ...rect }));
  }
  const split = splitIndex(shares);
  const first = shares.slice(0, split);
  const ratio = sumOf(first) / sumOf(shares);
  const wide = rect.w >= rect.h;
  const head: Rect = wide ? { ...rect, w: rect.w * ratio } : { ...rect, h: rect.h * ratio };
  const tail: Rect = wide
    ? { ...rect, x: rect.x + head.w, w: rect.w - head.w }
    : { ...rect, y: rect.y + head.h, h: rect.h - head.h };
  return [...layoutTiles(first, head), ...layoutTiles(shares.slice(split), tail)];
}

/** Eine zufällige Kachel, die nicht `previous` ist (außer es gibt keine andere). */
function pickOther(ids: readonly string[], previous: string, random: Random): string {
  const pool = ids.length > 1 ? ids.filter((id) => id !== previous) : ids;
  return pool[Math.min(Math.floor(random() * pool.length), pool.length - 1)] ?? previous;
}

/**
 * Die Folge der beleuchteten Kacheln: zufällig, nie zweimal dieselbe hintereinander (bei mehr als
 * einer Kachel) und mit dem Gewinner `winner` als letzter.
 */
export function spotlightSequence(
  ids: readonly string[],
  winner: string,
  random: Random,
  steps: number = SPOTLIGHT_STEPS,
): string[] {
  const backwards = [winner];
  for (let step = 1; step < steps; step += 1) {
    backwards.push(pickOther(ids, backwards[step - 1] ?? winner, random));
  }
  return backwards.reverse();
}

/** Verweildauer in ms nach Sprung `index` von `count`: wächst kubisch. */
export function spotlightDelay(index: number, count: number): number {
  const ratio = index / Math.max(count - 1, 1);
  return lerp(
    SPOTLIGHT_MIN_DELAY_MS,
    SPOTLIGHT_MIN_DELAY_MS + SPOTLIGHT_DELAY_SPAN_MS,
    ratio ** SPOTLIGHT_DELAY_POWER,
  );
}
