import { css, html, svg } from 'lit';
import type { TemplateResult } from 'lit';
import { styleMap } from 'lit/directives/style-map.js';

import {
  FALLBACK_COLOR,
  SLOT_CELL_GAP,
  SLOT_CLIP_ID,
  SLOT_CYCLE_HEIGHT,
  SLOT_CYCLES,
  SLOT_FADE_HEIGHT,
  SLOT_FRAME_RADIUS,
  SLOT_FRAME_STROKE,
  SLOT_HALF,
  SLOT_LABEL_GAP,
  SLOT_MIN_LABEL_HEIGHT,
  SLOT_PAYLINE_ARROW,
  SLOT_PAYLINE_WIDTH,
  SLOT_RECOIL_MS,
  SLOT_REEL_HEIGHT,
  SLOT_REEL_RADIUS,
  SLOT_REEL_WIDTH,
  SLOT_REEL_X,
  SLOT_REEL_Y,
  SLOT_SPIN_MS,
  SLOT_TARGET_CYCLE,
  SLOT_VIEW_HEIGHT,
  SLOT_VIEW_WIDTH,
  SLOT_WIN_CLASS,
  STAGE_TAGS,
} from '../constants/index.ts';
import { numberText, percentText } from './format.ts';
import { lerp } from './motion.ts';
import type { MotionToken } from './motion.ts';
import {
  brakeProgress,
  cellIndexAt,
  layoutCells,
  rebase,
  recoilPosition,
  startPosition,
  stripOffset,
  targetPosition,
} from './slot-geometry.ts';
import type { SlotCell } from './slot-geometry.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import { baseStyles, tokenStyles } from './styles.ts';

const STRIP_CLASS = 'strip';
const REEL_MIDDLE = SLOT_REEL_HEIGHT * SLOT_HALF;
const CYCLE_INDEXES = Array.from({ length: SLOT_CYCLES }, (_unused, index) => index);

/** Slot-Maschine (SVG): eine Walze mit allen Personen, Zeilenhöhe nach Chance, Gewinnlinie in der Mitte. */
export class TwSlot extends StageElement {
  static override properties = {
    ...StageElement.properties,
    _winner: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: block;
        width: 100%;
        height: 100%;
      }
      svg {
        display: block;
        width: 100%;
        height: 100%;
      }
      .frame {
        fill: var(--tw-color-fill);
        stroke: var(--tw-color-rim);
        stroke-width: ${SLOT_FRAME_STROKE}px;
      }
      .window {
        fill: var(--tw-color-surface);
      }
      .strip {
        will-change: transform;
      }
      .cell {
        stroke: var(--tw-color-surface);
        stroke-width: ${SLOT_CELL_GAP}px;
      }
      .win .cell {
        stroke: var(--tw-color-rim);
        stroke-width: ${SLOT_FRAME_STROKE}px;
      }
      .name {
        font: 900 20px sans-serif;
      }
      .chance {
        font: 500 13px sans-serif;
        opacity: 0.85;
      }
      text {
        fill: #ffffff;
        dominant-baseline: central;
        pointer-events: none;
      }
      .name {
        text-anchor: end;
      }
      .chance {
        text-anchor: start;
      }
      .payline {
        stroke: var(--tw-color-rim);
        stroke-width: ${SLOT_PAYLINE_WIDTH}px;
      }
      .arrow {
        fill: var(--tw-color-rim);
      }
      .fade {
        fill: #000000;
        pointer-events: none;
      }
    `,
  ];

  declare _winner: string | undefined;

  /** Zufallsquelle für die Landeposition im Gewinnersegment (für Tests ersetzbar). */
  random: () => number = Math.random;

  #cells: readonly SlotCell[] = [];
  #position = 0;

  /** Id der Person, die gerade unter der Gewinnlinie steht (für Anzeige und Tests). */
  get landedId(): string | undefined {
    return this.#cells[cellIndexAt(this.#cells, this.#position)]?.id;
  }

  protected reset(): void {
    this.#cells = layoutCells(sharesOf(this.segments));
    this.#position = startPosition();
    this._winner = undefined;
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    const target = this.#target(id);
    if (target === undefined) {
      return;
    }
    this._winner = undefined;
    this.#move(rebase(this.#position));
    const from = this.#position;
    await token.frames(SLOT_RECOIL_MS, (progress) => {
      this.#move(recoilPosition(from, progress));
    });
    const start = this.#position;
    await token.frames(SLOT_SPIN_MS, (progress) => {
      this.#move(lerp(start, target, brakeProgress(progress)));
    });
    if (!token.dead) {
      this.#move(target);
      this._winner = id;
    }
  }

  protected settle(id: string): void {
    const target = this.#target(id);
    if (target !== undefined) {
      this.#move(target);
      this._winner = id;
    }
  }

  protected override render(): TemplateResult {
    const transform = `translate3d(0, ${numberText(stripOffset(this.#position))}px, 0)`;
    const [width, height, reelX, reelY] = [
      SLOT_VIEW_WIDTH,
      SLOT_VIEW_HEIGHT,
      SLOT_REEL_X,
      SLOT_REEL_Y,
    ].map(numberText) as [string, string, string, string];
    return html`
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label=${this.label}>
        <rect
          class="frame"
          x=${SLOT_FRAME_STROKE * SLOT_HALF}
          y=${SLOT_FRAME_STROKE * SLOT_HALF}
          width=${SLOT_VIEW_WIDTH - SLOT_FRAME_STROKE}
          height=${SLOT_VIEW_HEIGHT - SLOT_FRAME_STROKE}
          rx=${SLOT_FRAME_RADIUS}
        ></rect>
        <clipPath id=${SLOT_CLIP_ID}>
          <rect
            x=${SLOT_REEL_X}
            y=${SLOT_REEL_Y}
            width=${SLOT_REEL_WIDTH}
            height=${SLOT_REEL_HEIGHT}
            rx=${SLOT_REEL_RADIUS}
          ></rect>
        </clipPath>
        <g clip-path="url(#${SLOT_CLIP_ID})">
          <rect
            class="window"
            x=${SLOT_REEL_X}
            y=${SLOT_REEL_Y}
            width=${SLOT_REEL_WIDTH}
            height=${SLOT_REEL_HEIGHT}
          ></rect>
          <g transform="translate(${reelX} ${reelY})">
            <g class=${STRIP_CLASS} style=${styleMap({ transform })}>
              ${CYCLE_INDEXES.map((cycle) => this.#cycle(cycle))}
            </g>
            ${this.#overlay()}
          </g>
        </g>
      </svg>
    `;
  }

  /** Die rechnerische Position (Streifen unter der Linie) setzen und sofort anzeigen. */
  #move(position: number): void {
    this.#position = position;
    const strip = this.renderRoot.querySelector<SVGGElement>(`.${STRIP_CLASS}`);
    strip?.style.setProperty(
      'transform',
      `translate3d(0, ${numberText(stripOffset(position))}px, 0)`,
    );
  }

  #target(id: string): number | undefined {
    const cell = this.#cells.find((candidate) => candidate.id === id);
    return cell && targetPosition(cell, this.random());
  }

  #cycle(cycle: number): TemplateResult[] {
    return this.#cells.map((cell) => {
      const winner = cycle === SLOT_TARGET_CYCLE && cell.id === this._winner;
      const y = cycle * SLOT_CYCLE_HEIGHT + cell.top;
      return svg`<g class=${winner ? SLOT_WIN_CLASS : ''}>${this.#row(cell, y)}</g>`;
    });
  }

  #row(cell: SlotCell, y: number): TemplateResult {
    const rect = svg`<rect class="cell" x="0" y=${y} width=${SLOT_REEL_WIDTH} height=${cell.height} fill=${cell.color || FALLBACK_COLOR}></rect>`;
    if (cell.height < SLOT_MIN_LABEL_HEIGHT) {
      return rect;
    }
    const middle = y + cell.height * SLOT_HALF;
    const centre = SLOT_REEL_WIDTH * SLOT_HALF;
    return svg`${rect}
      <text class="name" x=${centre - SLOT_LABEL_GAP * SLOT_HALF} y=${middle}>${cell.label}</text>
      <text class="chance" x=${centre + SLOT_LABEL_GAP} y=${middle}>${percentText(cell.share)}</text>`;
  }

  /** Verlauf an Ober- und Unterkante und die Gewinnlinie mit Pfeilen. */
  #overlay(): TemplateResult {
    const arrow = SLOT_PAYLINE_ARROW;
    const left = `0,${numberText(REEL_MIDDLE - arrow)} ${numberText(arrow)},${numberText(REEL_MIDDLE)} 0,${numberText(REEL_MIDDLE + arrow)}`;
    const right = `${numberText(SLOT_REEL_WIDTH)},${numberText(REEL_MIDDLE - arrow)} ${numberText(SLOT_REEL_WIDTH - arrow)},${numberText(REEL_MIDDLE)} ${numberText(SLOT_REEL_WIDTH)},${numberText(REEL_MIDDLE + arrow)}`;
    return svg`
      <rect class="fade" x="0" y="0" width=${SLOT_REEL_WIDTH} height=${SLOT_FADE_HEIGHT} opacity="0.25"></rect>
      <rect class="fade" x="0" y=${SLOT_REEL_HEIGHT - SLOT_FADE_HEIGHT} width=${SLOT_REEL_WIDTH} height=${SLOT_FADE_HEIGHT} opacity="0.25"></rect>
      <line class="payline" x1="0" x2=${SLOT_REEL_WIDTH} y1=${REEL_MIDDLE} y2=${REEL_MIDDLE}></line>
      <polygon class="arrow" points=${left}></polygon>
      <polygon class="arrow" points=${right}></polygon>`;
  }
}

customElements.define(STAGE_TAGS.slot, TwSlot);
