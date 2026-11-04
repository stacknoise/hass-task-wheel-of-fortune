import { LitElement } from 'lit';
import type { PropertyValues } from 'lit';

import { EVENT_WHEEL_STOP } from '../constants/index.ts';
import { MotionToken, prefersReducedMotion } from './motion.ts';
import type { WheelSegment } from './wheel-geometry.ts';

/** Gemeinsame Chancen: Anteil je Segment an der Summe (Segmente ohne Chance entfallen). */
export interface Share extends WheelSegment {
  readonly share: number;
}

export function sharesOf(segments: readonly WheelSegment[]): readonly Share[] {
  const drawable = segments.filter((segment) => segment.chance > 0);
  const total = drawable.reduce((sum, segment) => sum + segment.chance, 0);
  return drawable.map((segment) => ({ ...segment, share: segment.chance / total }));
}

/** Was jede Auslosungs-Animation anbietet (auch das Glücksrad). */
export interface Stage extends HTMLElement {
  segments: readonly WheelSegment[];
  label: string;
  /** Name der Aufgabe und Sprache für Animationen mit Text (Eilmeldung, Oscar-Verleihung). */
  taskName?: string;
  language?: string;
  /** Spielt die Animation zum Gewinner `id`; fertig, wenn sie steht. Das Ergebnis steht vorher fest. */
  spinTo(id: string): Promise<void>;
}

/**
 * Grundgerüst der Animationen (alle außer dem Glücksrad).
 *
 * `spinTo` ist die Schablone: unbekannte Gewinner werden ignoriert, bei reduzierter Bewegung springt
 * die Animation mit `settle` direkt ans Ziel, sonst läuft `play`. Neue Segmente und Entfernen
 * aus dem Dokument brechen eine laufende Animation ab.
 */
export abstract class StageElement extends LitElement implements Stage {
  static override properties = {
    segments: { attribute: false },
    label: { type: String },
    taskName: { type: String },
    language: { type: String },
  };

  declare segments: readonly WheelSegment[];
  declare label: string;
  declare taskName: string;
  declare language: string;

  #token = new MotionToken();

  constructor() {
    super();
    this.segments = [];
    this.label = '';
    this.taskName = '';
    this.language = '';
  }

  async spinTo(id: string): Promise<void> {
    if (!this.segments.some((segment) => segment.id === id && segment.chance > 0)) {
      return;
    }
    await this.updateComplete;
    this.#token.cancel();
    const token = (this.#token = new MotionToken());
    if (prefersReducedMotion()) {
      this.settle(id);
    } else {
      await this.play(id, token);
    }
    if (!token.dead) {
      this.dispatchEvent(new CustomEvent(EVENT_WHEEL_STOP, { detail: id }));
    }
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.#token.cancel();
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('segments') || changed.has('taskName')) {
      this.#token.cancel();
      this.reset();
    }
  }

  /** Setzt die Bühne auf den Anfang zurück (neue Segmente). */
  protected abstract reset(): void;

  /** Spielt die Animation bis zum Gewinner `id`; endet, wenn sie steht. */
  protected abstract play(id: string, token: MotionToken): Promise<void>;

  /** Zeigt den Endstand für `id` ohne Bewegung. */
  protected abstract settle(id: string): void;
}
