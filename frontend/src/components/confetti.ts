import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import {
  CONFETTI_COLUMN_STEP,
  CONFETTI_COUNT,
  CONFETTI_DELAY_CYCLE,
  CONFETTI_DELAY_STEP_MS,
  CONFETTI_DURATION_CYCLE,
  CONFETTI_DURATION_MS,
  CONFETTI_DURATION_SPREAD_MS,
  CONFETTI_PALETTE,
  COMPONENT_TAGS,
  PERCENT,
} from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

interface Piece {
  readonly left: number;
  readonly color: string;
  readonly delay: number;
  readonly duration: number;
}

/** Bahnen der Konfettistücke, fest berechnet: reine Dekoration, kein Zufall nötig. */
const PIECES: readonly Piece[] = Array.from({ length: CONFETTI_COUNT }, (_, index) => ({
  left: (index * CONFETTI_COLUMN_STEP) % PERCENT,
  color: CONFETTI_PALETTE[index % CONFETTI_PALETTE.length] ?? CONFETTI_PALETTE[0],
  delay: (index % CONFETTI_DELAY_CYCLE) * CONFETTI_DELAY_STEP_MS,
  duration: CONFETTI_DURATION_MS + (index % CONFETTI_DURATION_CYCLE) * CONFETTI_DURATION_SPREAD_MS,
}));

/** Konfettiregen über der Fläche des Elternelements; bei reduzierter Bewegung unsichtbar. */
export class TwConfetti extends LitElement {
  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        position: absolute;
        inset: 0;
        overflow: hidden;
        pointer-events: none;
      }
      span {
        position: absolute;
        top: 0;
        width: 8px;
        height: 14px;
        border-radius: 2px;
        animation: fall var(--tw-fall, 2600ms) ease-in var(--tw-delay, 0ms) both;
      }
      @keyframes fall {
        from {
          transform: translateY(-40px) rotate(0deg);
          opacity: 1;
        }
        to {
          transform: translateY(460px) rotate(540deg);
          opacity: 0;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        :host {
          display: none;
        }
      }
    `,
  ];

  protected override render(): TemplateResult {
    return html`${PIECES.map(
      (piece) =>
        html`<span
          style="left:${piece.left}%;background:${piece.color};--tw-delay:${piece.delay}ms;--tw-fall:${piece.duration}ms"
        ></span>`,
    )}`;
  }
}

defineOnce(COMPONENT_TAGS.confetti, TwConfetti);
