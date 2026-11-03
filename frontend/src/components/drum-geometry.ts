import {
  DRUM_BOUNCE,
  DRUM_CENTER_X,
  DRUM_CENTER_Y,
  DRUM_DAMPING,
  DRUM_EXIT_INSET,
  DRUM_GRAVITY,
  DRUM_KICK_RATE,
  DRUM_KICK_SPEED,
  DRUM_LANDED_DISTANCE,
  DRUM_MIN_DISTANCE,
  DRUM_PHASE_MS,
  DRUM_POP_SCALE,
  DRUM_RADIUS,
  DRUM_REST_RATE,
  DRUM_RUN_STEP_SECONDS,
  DRUM_QUARTER_TURN,
  DRUM_SPIN_DROP,
  DRUM_TAU,
  DRUM_SPIN_FROM,
  DRUM_SUBSTEPS,
  DRUM_TRAY_X,
  DRUM_TRAY_Y,
  DRUM_WALL_INSET,
  DRUM_WARMUP_SECONDS,
  DRUM_WARMUP_STEPS,
} from '../constants/index.ts';
import { easeInOut, lerp, randomBetween } from './motion.ts';
import { createBalls, pickBall } from './drum-balls.ts';
import type { Ball, Random } from './drum-balls.ts';
import type { Point } from './drum-shapes.ts';
import type { Share } from './stage-base.ts';

const TRAY: Point = { x: DRUM_TRAY_X, y: DRUM_TRAY_Y };
const PHASE_COUNT = DRUM_PHASE_MS.length;
const TOTAL_MS = DRUM_PHASE_MS.reduce((sum, ms) => sum + ms, 0);
const NO_PIN = -1;

export const DRUM_TOTAL_MS = TOTAL_MS;

function integrate(ball: Ball, dt: number, angle: number, kick: number, random: Random): void {
  ball.vx += Math.sin(angle) * DRUM_GRAVITY * dt;
  ball.vy += Math.cos(angle) * DRUM_GRAVITY * dt;
  if (kick > 0 && random() < kick * dt) {
    ball.vx += randomBetween(-DRUM_KICK_SPEED, DRUM_KICK_SPEED, random);
    ball.vy += randomBetween(-DRUM_KICK_SPEED, DRUM_KICK_SPEED, random);
  }
  ball.vx *= DRUM_DAMPING;
  ball.vy *= DRUM_DAMPING;
  ball.x += ball.vx * dt;
  ball.y += ball.vy * dt;
}

/** Hält die Kugel in der Trommel und lässt sie an der Wand abprallen. */
function contain(ball: Ball): void {
  const dx = ball.x - DRUM_CENTER_X;
  const dy = ball.y - DRUM_CENTER_Y;
  const distance = Math.hypot(dx, dy);
  const limit = DRUM_RADIUS - DRUM_WALL_INSET - ball.r;
  if (distance <= limit) {
    return;
  }
  const nx = dx / distance;
  const ny = dy / distance;
  ball.x = DRUM_CENTER_X + nx * limit;
  ball.y = DRUM_CENTER_Y + ny * limit;
  const normal = ball.vx * nx + ball.vy * ny;
  if (normal > 0) {
    ball.vx -= DRUM_BOUNCE * normal * nx;
    ball.vy -= DRUM_BOUNCE * normal * ny;
  }
}

/** Schiebt zwei überlappende Kugeln auseinander (nach Masse, die geführte Kugel bleibt stehen) und stößt sie ab. */
function collide(first: Ball, second: Ball, pinned: readonly [boolean, boolean]): void {
  const dx = second.x - first.x;
  const dy = second.y - first.y;
  const distance = Math.hypot(dx, dy);
  const reach = first.r + second.r;
  if (distance >= reach || distance <= DRUM_MIN_DISTANCE) {
    return;
  }
  const ux = dx / distance;
  const uy = dy / distance;
  const wFirst = pinned[0] ? 0 : 1 / (first.r * first.r);
  const wSecond = pinned[1] ? 0 : 1 / (second.r * second.r);
  const total = wFirst + wSecond;
  if (total === 0) {
    return;
  }
  const overlap = reach - distance;
  first.x -= (ux * overlap * wFirst) / total;
  first.y -= (uy * overlap * wFirst) / total;
  second.x += (ux * overlap * wSecond) / total;
  second.y += (uy * overlap * wSecond) / total;
  const approach = (second.vx - first.vx) * ux + (second.vy - first.vy) * uy;
  if (approach < 0) {
    const impulse = (-DRUM_BOUNCE * approach) / total;
    first.vx -= impulse * wFirst * ux;
    first.vy -= impulse * wFirst * uy;
    second.vx += impulse * wSecond * ux;
    second.vy += impulse * wSecond * uy;
  }
}

/** Dreht `angle` sanft auf das nächste Vielfache einer vollen Umdrehung (Öffnung unten rechts). */
function toRest(angle: number, dt: number): number {
  const rest = Math.round(angle / DRUM_TAU) * DRUM_TAU;
  return angle + (rest - angle) * Math.min(1, dt * DRUM_REST_RATE);
}

type Phase = (local: number, dt: number) => void;

/**
 * Die Simulation der Lostrommel: rotierende Schwerkraft, Kollisionen, und eine kinematisch geführte
 * Gewinnerkugel, die zur Öffnung gelenkt wird und in die Ablage rollt. Der Zufall (Startlage, Stöße)
 * ändert nie das Ergebnis: die Gewinnerkugel erreicht immer die Ablage.
 */
export class DrumSimulation {
  readonly balls: Ball[];
  angle = 0;
  #target: Ball | undefined;
  #from: Point | undefined;
  readonly #random: Random;
  readonly #phases: readonly Phase[];

  constructor(shares: readonly Share[], random: Random = Math.random) {
    this.#random = random;
    this.balls = createBalls(shares, random);
    this.#phases = [
      (local, dt) => {
        this.#tumble(local, dt);
      },
      (local, dt) => {
        this.#guide(local, dt);
      },
      (local, dt) => {
        this.#drop(local, dt);
      },
      (local, dt) => {
        this.#pop(local, dt);
      },
    ];
    for (let n = 0; n < DRUM_WARMUP_STEPS; n += 1) {
      this.step(DRUM_WARMUP_SECONDS, 0, NO_PIN);
    }
  }

  /** Die Kugel, die in die Ablage rollt. */
  get target(): Ball | undefined {
    return this.#target;
  }

  /** Legt die Gewinnerkugel fest (Person `id`, Anteil `fraction` im Segment). */
  choose(id: string, fraction: number): void {
    this.#target = pickBall(this.balls, id, fraction);
    this.#from = undefined;
  }

  /** Ein Zeitschritt: Schwerkraft nach `angle`, Stöße (`kick`/s), Wand und Kollisionen. */
  step(dt: number, kick: number, pinned: number): void {
    this.balls.forEach((ball, index) => {
      if (!ball.out && index !== pinned) {
        integrate(ball, dt, this.angle, kick, this.#random);
        contain(ball);
      }
    });
    this.balls.forEach((first, i) => {
      this.balls.slice(i + 1).forEach((second, offset) => {
        if (!first.out && !second.out) {
          collide(first, second, [i === pinned, i + 1 + offset === pinned]);
        }
      });
    });
  }

  /** Setzt die Simulation um `elapsed` ms seit dem Start des Laufs fort. */
  advance(elapsed: number, seconds: number): void {
    const dt = Math.min(DRUM_RUN_STEP_SECONDS, seconds);
    let rest = Math.min(elapsed, TOTAL_MS);
    let index = 0;
    while (index < PHASE_COUNT - 1 && rest >= (DRUM_PHASE_MS[index] ?? 0)) {
      rest -= DRUM_PHASE_MS[index] ?? 0;
      index += 1;
    }
    const duration = DRUM_PHASE_MS[index] ?? 1;
    this.#phases[index]?.(Math.min(1, rest / duration), dt);
  }

  /** Zeigt den Endstand: die Gewinnerkugel liegt vergrößert in der Ablage, die Trommel steht. */
  finish(): void {
    const target = this.#target;
    if (target) {
      target.out = true;
      target.x = TRAY.x;
      target.y = TRAY.y;
      target.scale = 1 + DRUM_POP_SCALE;
    }
    this.angle = 0;
  }

  /** Die Person, deren Kugel in der Ablage liegt. */
  landedId(): string | undefined {
    return this.balls.find(
      (ball) => Math.hypot(ball.x - TRAY.x, ball.y - TRAY.y) < DRUM_LANDED_DISTANCE,
    )?.id;
  }

  /** Zwei halbe Zeitschritte, damit schnelle Kugeln nicht durcheinander hindurchfliegen. */
  #substeps(dt: number, kick: number, pinned: number): void {
    for (let n = 0; n < DRUM_SUBSTEPS; n += 1) {
      this.step(dt / DRUM_SUBSTEPS, kick, pinned);
    }
  }

  #tumble(local: number, dt: number): void {
    this.angle += lerp(DRUM_SPIN_FROM, DRUM_SPIN_FROM - DRUM_SPIN_DROP, local) * dt;
    this.#substeps(dt, DRUM_KICK_RATE, NO_PIN);
  }

  /** Die Öffnung der Trommel für die Kugel `target`: unten rechts an der Wand. */
  #exit(target: Ball): Point {
    const reach = (DRUM_RADIUS - target.r - DRUM_EXIT_INSET) * Math.SQRT1_2;
    return { x: DRUM_CENTER_X + reach, y: DRUM_CENTER_Y + reach };
  }

  #guide(local: number, dt: number): void {
    const target = this.#target;
    if (target) {
      const from = (this.#from ??= { x: target.x, y: target.y });
      const exit = this.#exit(target);
      const eased = easeInOut(local);
      target.x = lerp(from.x, exit.x, eased);
      target.y = lerp(from.y, exit.y, eased);
    }
    this.angle = toRest(this.angle, dt);
    const pinned = target ? this.balls.indexOf(target) : NO_PIN;
    this.#substeps(dt, 0, pinned);
  }

  #drop(local: number, dt: number): void {
    const target = this.#target;
    if (target) {
      const exit = this.#exit(target);
      target.out = true;
      target.x = lerp(exit.x, TRAY.x, local * local);
      target.y = lerp(exit.y, TRAY.y, local * local);
    }
    this.angle = toRest(this.angle, dt);
    this.step(dt, 0, NO_PIN);
  }

  #pop(local: number, dt: number): void {
    const target = this.#target;
    if (target) {
      target.out = true;
      target.x = TRAY.x;
      target.y = TRAY.y;
      target.scale = 1 + DRUM_POP_SCALE * Math.sin(local * DRUM_QUARTER_TURN);
    }
    this.step(dt, 0, NO_PIN);
  }
}
