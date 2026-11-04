import { EASE_QUADRATIC, REDUCED_MOTION_QUERY } from '../constants/index.ts';

/**
 * Bricht eine laufende Animation ab: Zeitgeber und Bildfolgen hören auf, ihre Versprechen bleiben
 * offen. Wer auf das Ende wartet, wartet zusätzlich auf `cancelled`, damit er nicht hängen bleibt.
 */
export class MotionToken {
  #dead = false;
  #raf = 0;
  readonly #timers = new Set<ReturnType<typeof setTimeout>>();
  #resolveCancelled: () => void = () => undefined;
  readonly #cancelled = new Promise<void>((resolve) => {
    this.#resolveCancelled = resolve;
  });

  /** Wird erfüllt, sobald die Animation abgebrochen wurde. */
  get cancelled(): Promise<void> {
    return this.#cancelled;
  }

  get dead(): boolean {
    return this.#dead;
  }

  cancel(): void {
    this.#dead = true;
    cancelAnimationFrame(this.#raf);
    this.#timers.forEach(clearTimeout);
    this.#timers.clear();
    this.#resolveCancelled();
  }

  /** Wartet `ms` Millisekunden; nach einem Abbruch wird das Versprechen nie erfüllt. */
  sleep(ms: number): Promise<void> {
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.#timers.delete(timer);
        resolve();
      }, ms);
      this.#timers.add(timer);
    });
  }

  /**
   * Ruft `step(fortschritt 0..1, vergangeneMs)` je Bild auf, bis `durationMs` um sind.
   * Nach einem Abbruch endet die Folge ohne weiteren Aufruf.
   */
  frames(durationMs: number, step: (progress: number, elapsedMs: number) => void): Promise<void> {
    return new Promise((resolve) => {
      let start: number | undefined;
      let last = 0;
      const tick = (now: number): void => {
        if (this.#dead) {
          return;
        }
        start ??= now;
        const progress = Math.min(1, (now - start) / durationMs);
        step(progress, now - (last || now));
        last = now;
        if (progress < 1) {
          this.#raf = requestAnimationFrame(tick);
        } else {
          resolve();
        }
      };
      this.#raf = requestAnimationFrame(tick);
    });
  }
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

export function lerp(from: number, to: number, progress: number): number {
  return from + (to - from) * progress;
}

/** Sanfter Anlauf und Auslauf (0..1 auf 0..1). */
export function easeInOut(progress: number): number {
  return progress < 1 / EASE_QUADRATIC
    ? EASE_QUADRATIC * progress * progress
    : 1 - (-EASE_QUADRATIC * progress + EASE_QUADRATIC) ** EASE_QUADRATIC / EASE_QUADRATIC;
}

export function randomBetween(
  low: number,
  high: number,
  random: () => number = Math.random,
): number {
  return lerp(low, high, random());
}
