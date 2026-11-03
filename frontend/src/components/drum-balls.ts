import {
  DRUM_BALLS_PER_PERSON,
  DRUM_CENTER_X,
  DRUM_CENTER_Y,
  DRUM_RADIUS,
  DRUM_RADIUS_FACTOR,
  DRUM_SPAWN_INSET,
  DRUM_TAU,
  PERCENT,
} from '../constants/index.ts';
import { randomBetween } from './motion.ts';
import type { Share } from './stage-base.ts';

export type Random = () => number;

/** Eine Kugel der Trommel (veränderlich; die Simulation schreibt Ort und Geschwindigkeit fort). */
export interface Ball {
  readonly id: string;
  readonly label: string;
  readonly color: string;
  readonly r: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  /** Außerhalb der Trommel: nimmt an keiner Kollision mehr teil. */
  out: boolean;
  scale: number;
}

/** Je Person drei Kugeln; der Radius wächst mit der Wurzel der Chance in Prozent (Fläche ∝ Chance). */
export function createBalls(shares: readonly Share[], random: Random): Ball[] {
  return shares.flatMap((share) =>
    Array.from({ length: DRUM_BALLS_PER_PERSON }, () => {
      const r = DRUM_RADIUS_FACTOR * Math.sqrt(share.share * PERCENT);
      const angle = randomBetween(0, DRUM_TAU, random);
      const distance = randomBetween(0, DRUM_RADIUS - r - DRUM_SPAWN_INSET, random);
      return {
        id: share.id,
        label: share.label,
        color: share.color,
        r,
        x: DRUM_CENTER_X + Math.cos(angle) * distance,
        y: DRUM_CENTER_Y + Math.sin(angle) * distance,
        vx: 0,
        vy: 0,
        out: false,
        scale: 1,
      };
    }),
  );
}

/** Wählt unter den Kugeln der Person `id` die, auf die der Anteil `fraction` (0..1) im Segment fällt. */
export function pickBall(balls: readonly Ball[], id: string, fraction: number): Ball | undefined {
  const mine = balls.filter((ball) => ball.id === id);
  return mine[Math.min(mine.length - 1, Math.floor(fraction * mine.length))];
}
