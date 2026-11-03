import { LitElement, css, html, svg } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { styleMap } from 'lit/directives/style-map.js';

import {
  COMPONENT_TAGS,
  EVENT_WHEEL_STOP,
  MIN_LABEL_CHANCE,
  REDUCED_MOTION_QUERY,
  SPIN_DURATION_MS,
  SPIN_EASING,
  SPIN_SETTLE_MS,
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
import { numberText, percentText } from './format.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { layoutWedges, spinRotation, wedgePath } from './wheel-geometry.ts';
import type { Wedge, WheelSegment } from './wheel-geometry.ts';

const ROTOR_CLASS = 'rotor';
const [LEFT, RIGHT, TIP_X, TIP_Y] = [
  WHEEL_CENTER - WHEEL_POINTER_HALF_WIDTH,
  WHEEL_CENTER + WHEEL_POINTER_HALF_WIDTH,
  WHEEL_CENTER,
  WHEEL_POINTER_DEPTH,
].map(numberText) as [string, string, string, string];
const POINTER = `M${LEFT} 0 L${RIGHT} 0 L${TIP_X} ${TIP_Y} Z`;

/** Glücksrad (SVG). Zeigt Segmente nach Chance und dreht auf Anforderung zu einem vorgegebenen Segment. */
export class TwWheel extends LitElement {
  static override properties = {
    segments: { attribute: false },
    label: { type: String },
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
        fill: var(--tw-color-divider);
      }
      .rotor {
        transform-origin: ${WHEEL_CENTER}px ${WHEEL_CENTER}px;
        will-change: transform;
      }
      .wedge {
        stroke: #ffffff;
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
        fill: #ffffff;
        text-anchor: middle;
        pointer-events: none;
      }
      .pointer {
        fill: #ffffff;
        stroke: var(--tw-color-stage);
        stroke-width: ${WHEEL_SEGMENT_GAP}px;
      }
    `,
  ];

  declare segments: readonly WheelSegment[];
  declare label: string;
  declare _rotation: number;
  declare _animated: boolean;

  #wedges: readonly Wedge[] = [];

  constructor() {
    super();
    this.segments = [];
    this.label = '';
    this._rotation = 0;
    this._animated = false;
  }

  /**
   * Dreht das Rad so, dass das Segment `id` unter dem Zeiger steht; fertig, wenn es steht.
   * Bei reduzierter Bewegung springt das Rad ohne Animation.
   */
  async spinTo(id: string): Promise<void> {
    const wedge = this.#wedges.find((candidate) => candidate.id === id);
    if (!wedge) {
      return;
    }
    await this.updateComplete;
    const animate = !window.matchMedia(REDUCED_MOTION_QUERY).matches;
    this.#flushStyles();
    this._animated = animate;
    this._rotation = spinRotation(this._rotation, wedge.mid);
    if (animate) {
      await this.#settled();
    }
    this.dispatchEvent(new CustomEvent(EVENT_WHEEL_STOP, { detail: id }));
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('segments')) {
      this.#wedges = layoutWedges(this.segments);
      this._rotation = 0;
      this._animated = false;
    }
  }

  protected override render(): TemplateResult {
    const rotor = styleMap({
      transform: `rotate(${numberText(this._rotation)}deg)`,
      transition: this._animated
        ? `transform ${numberText(SPIN_DURATION_MS)}ms ${SPIN_EASING}`
        : 'none',
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
                (wedge) => this.#wedge(wedge),
              )}
            </g>`
        }
        <path class="pointer" d=${POINTER}></path>
      </svg>
    `;
  }

  #wedge(wedge: Wedge): TemplateResult {
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
      <text class="chance" x=${WHEEL_CENTER} y=${WHEEL_CENTER - WHEEL_CHANCE_RADIUS} transform=${turn}>${percentText(wedge.share)}</text>`;
  }

  /** Erzwingt, dass der Stand ohne Übergang (Drehung 0) berechnet ist, bevor die Drehung beginnt. */
  #flushStyles(): void {
    this.renderRoot.querySelector(`.${ROTOR_CLASS}`)?.getBoundingClientRect();
  }

  /** Wartet auf das Ende des Übergangs; ein Zeitgeber fängt den Fall ab, dass er nie gemeldet wird. */
  #settled(): Promise<void> {
    const rotor = this.renderRoot.querySelector(`.${ROTOR_CLASS}`);
    return new Promise((resolve) => {
      const finish = (): void => {
        clearTimeout(timer);
        rotor?.removeEventListener('transitionend', finish);
        resolve();
      };
      const timer = setTimeout(finish, SPIN_DURATION_MS + SPIN_SETTLE_MS);
      rotor?.addEventListener('transitionend', finish);
    });
  }
}

customElements.define(COMPONENT_TAGS.wheel, TwWheel);
