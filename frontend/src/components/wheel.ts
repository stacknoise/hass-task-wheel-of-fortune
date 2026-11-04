import { css, html, svg } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { styleMap } from 'lit/directives/style-map.js';

import {
  COMPONENT_TAGS,
  MIN_LABEL_CHANCE,
  SPIN_DURATION_MS,
  SPIN_EASING,
  SPIN_SETTLE_MS,
  TRANSITION_NONE,
  WHEEL_CENTER,
  WHEEL_CHANCE_RADIUS,
  WHEEL_NAME_RADIUS,
  WHEEL_POINTER_DEPTH,
  WHEEL_POINTER_HALF_WIDTH,
  WHEEL_RADIUS,
  WHEEL_RIM_RADIUS,
  WHEEL_SEGMENT_GAP,
  WHEEL_VIEWBOX,
} from '../constants/index.ts';
import { formatPercent } from '../i18n/format.ts';
import { numberText } from './format.ts';
import type { MotionToken } from './motion.ts';
import { StageElement } from './stage-base.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { layoutWedges, spinRotation, wedgePath } from './wheel-geometry.ts';
import type { Wedge } from './wheel-geometry.ts';
import { defineOnce } from './define.ts';

const ROTOR_CLASS = 'rotor';
const [LEFT, RIGHT, TIP_X, TIP_Y] = [
  WHEEL_CENTER - WHEEL_POINTER_HALF_WIDTH,
  WHEEL_CENTER + WHEEL_POINTER_HALF_WIDTH,
  WHEEL_CENTER,
  WHEEL_POINTER_DEPTH,
].map(numberText) as [string, string, string, string];
const POINTER = `M${LEFT} 0 L${RIGHT} 0 L${TIP_X} ${TIP_Y} Z`;

/** Glücksrad (SVG). Zeigt Segmente nach Chance und dreht auf Anforderung zu einem vorgegebenen Segment. */
export class TwWheel extends StageElement {
  static override properties = {
    ...StageElement.properties,
    _rotation: { state: true },
    _animated: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      svg {
        display: block;
        width: 100%;
        height: 100%;
      }
      .rim {
        fill: var(--tw-color-rim);
      }
      .empty {
        fill: var(--tw-color-surface);
        stroke: var(--tw-color-divider);
        stroke-width: 1px;
      }
      .rotor {
        transform-origin: ${WHEEL_CENTER}px ${WHEEL_CENTER}px;
        will-change: transform;
      }
      .wedge {
        stroke: var(--tw-color-surface);
        stroke-width: ${WHEEL_SEGMENT_GAP}px;
      }
      .name {
        font: 700 20px sans-serif;
      }
      .chance {
        font: 500 13px sans-serif;
        opacity: 0.85;
      }
      text {
        fill: var(--tw-color-white);
        text-anchor: middle;
        pointer-events: none;
      }
      .pointer {
        fill: var(--tw-color-text);
        stroke: var(--tw-color-surface);
        stroke-width: ${WHEEL_SEGMENT_GAP}px;
      }
    `,
  ];

  declare _rotation: number;
  declare _animated: boolean;

  #wedges: readonly Wedge[] = [];

  constructor() {
    super();
    this._rotation = 0;
    this._animated = false;
  }

  /** Neue Segmente: Stücke neu berechnen, Drehung zurück auf 0. */
  protected reset(): void {
    this.#wedges = layoutWedges(this.segments);
    this._rotation = 0;
    this._animated = false;
  }

  /** Springt ohne Übergang zum Gewinner. */
  protected settle(id: string): void {
    const wedge = this.#wedgeOf(id);
    if (wedge) {
      this._animated = false;
      this._rotation = spinRotation(this._rotation, wedge.mid);
    }
  }

  /** Dreht das Rad so, dass das Segment `id` unter dem Zeiger steht; fertig, wenn es steht. */
  protected async play(id: string, token: MotionToken): Promise<void> {
    const wedge = this.#wedgeOf(id);
    if (!wedge) {
      return;
    }
    this.#flushStyles();
    this._animated = true;
    this._rotation = spinRotation(this._rotation, wedge.mid);
    await Promise.race([token.sleep(SPIN_DURATION_MS + SPIN_SETTLE_MS), this.#transitionEnd()]);
  }

  #wedgeOf(id: string): Wedge | undefined {
    return this.#wedges.find((candidate) => candidate.id === id);
  }

  protected override render(): TemplateResult {
    const rotor = styleMap({
      transform: `rotate(${numberText(this._rotation)}deg)`,
      transition: this._animated
        ? `transform ${numberText(SPIN_DURATION_MS)}ms ${SPIN_EASING}`
        : TRANSITION_NONE,
    });
    return html`
      <svg viewBox="0 0 ${WHEEL_VIEWBOX} ${WHEEL_VIEWBOX}" role="img" aria-label=${this.label}>
        <circle class="rim" cx=${WHEEL_CENTER} cy=${WHEEL_CENTER} r=${WHEEL_RIM_RADIUS}></circle>
        ${
          this.#wedges.length === 0
            ? svg`<circle class="empty" cx=${WHEEL_CENTER} cy=${WHEEL_CENTER} r=${WHEEL_RADIUS}></circle>`
            : svg`<g class=${ROTOR_CLASS} style=${rotor}>
              ${repeat(
                this.#wedges,
                (wedge) => wedge.id,
                (wedge) => this.#wedgeShape(wedge),
              )}
            </g>`
        }
        <path class="pointer" d=${POINTER}></path>
      </svg>
    `;
  }

  #wedgeShape(wedge: Wedge): TemplateResult {
    const shape = wedge.full
      ? svg`<circle class="wedge" cx=${WHEEL_CENTER} cy=${WHEEL_CENTER} r=${WHEEL_RADIUS} fill=${wedge.color}></circle>`
      : svg`<path class="wedge" d=${wedgePath(wedge.start, wedge.end)} fill=${wedge.color}></path>`;
    if (wedge.share < MIN_LABEL_CHANCE) {
      return svg`${shape}`;
    }
    const centre = numberText(WHEEL_CENTER);
    const turn = `rotate(${numberText(wedge.mid)} ${centre} ${centre})`;
    return svg`${shape}
      <text class="name" x=${WHEEL_CENTER} y=${WHEEL_CENTER - WHEEL_NAME_RADIUS} transform=${turn}>${wedge.label}</text>
      <text class="chance" x=${WHEEL_CENTER} y=${WHEEL_CENTER - WHEEL_CHANCE_RADIUS} transform=${turn}>${formatPercent(wedge.share, this.language)}</text>`;
  }

  /** Erzwingt, dass der Stand ohne Übergang (Drehung 0) berechnet ist, bevor die Drehung beginnt. */
  #flushStyles(): void {
    this.renderRoot.querySelector(`.${ROTOR_CLASS}`)?.getBoundingClientRect();
  }

  /** Wird erfüllt, wenn der Übergang des Rotors endet; der Zeitgeber in `play` fängt den Fall ab, dass er nie gemeldet wird. */
  #transitionEnd(): Promise<void> {
    const rotor = this.renderRoot.querySelector(`.${ROTOR_CLASS}`);
    return new Promise((resolve) => {
      rotor?.addEventListener('transitionend', () => {
        resolve();
      });
    });
  }
}

defineOnce(COMPONENT_TAGS.wheel, TwWheel);
