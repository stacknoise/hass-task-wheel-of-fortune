import { css, html, nothing, svg } from 'lit';
import type { TemplateResult } from 'lit';

import {
  FALLBACK_COLOR,
  PLINKO_BALL_RADIUS,
  PLINKO_BALL_START_Y,
  PLINKO_BALL_STROKE,
  PLINKO_BIN_HEIGHT,
  PLINKO_BIN_TOP,
  PLINKO_BOARD_LEFT,
  PLINKO_BOARD_RIGHT,
  PLINKO_BOUNCE_COUNT,
  PLINKO_BOUNCE_HEIGHT,
  PLINKO_BOUNCE_MS,
  PLINKO_CHANCE_Y,
  PLINKO_GLOW_MS,
  PLINKO_HALF,
  PLINKO_MIN_CHANCE_WIDTH,
  PLINKO_MIN_NAME_WIDTH,
  PLINKO_NAME_Y,
  PLINKO_PEG_RADIUS,
  PLINKO_SEPARATOR_RISE,
  PLINKO_SEPARATOR_WIDTH,
  PLINKO_VIEW_HEIGHT,
  PLINKO_VIEW_WIDTH,
  PLINKO_WIN_CLASS,
  STAGE_TAGS,
} from '../constants/index.ts';
import { formatPercent } from '../i18n/format.ts';
import { numberText } from './format.ts';
import type { MotionToken } from './motion.ts';
import {
  PEGS,
  binAt,
  buildPath,
  landingPoint,
  layoutBins,
  positionAt,
  stepDurations,
} from './plinko-geometry.ts';
import type { BallState, Bin, PathPoint } from './plinko-geometry.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import { defineOnce } from './define.ts';
import { baseStyles, tokenStyles } from './styles.ts';

interface Ball {
  readonly x: number;
  readonly y: number;
}

const START_BALL: Ball = {
  x: (PLINKO_BOARD_LEFT + PLINKO_BOARD_RIGHT) * PLINKO_HALF,
  y: PLINKO_BALL_START_Y,
};
const NO_PEGS: ReadonlySet<string> = new Set();

/** Plinko (SVG): Stiftefeld, durch das eine Kugel in Fächer fällt; Fachbreite entspricht der Chance. */
export class TwPlinko extends StageElement {
  static override properties = {
    ...StageElement.properties,
    _ball: { state: true },
    _lit: { state: true },
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
      .peg {
        fill: var(--tw-color-neutral);
        transition: fill 0.3s;
      }
      .peg.lit {
        fill: var(--tw-color-rim);
      }
      .bin {
        stroke: none;
      }
      .win .bin {
        stroke: var(--tw-color-rim);
        stroke-width: 3px;
      }
      .separator {
        stroke: var(--tw-color-surface);
        stroke-linecap: round;
      }
      .ball {
        fill: var(--tw-color-rim);
        stroke: var(--tw-color-surface);
      }
      text {
        fill: var(--tw-color-white);
        text-anchor: middle;
        pointer-events: none;
      }
      .name {
        font: 900 16px sans-serif;
      }
      .chance {
        font: 500 14px sans-serif;
      }
    `,
  ];

  declare _ball: Ball;
  declare _lit: ReadonlySet<string>;
  declare _winner: string | undefined;

  /** Zufallsquelle für Weg und Landeplatz im Fach des Gewinners (für Tests ersetzbar). */
  random: () => number = Math.random;

  #bins: readonly Bin[] = [];
  #segment = -1;

  /** Id der Person, in deren Fach die Kugel gerade liegt (für Anzeige und Tests). */
  get landedId(): string | undefined {
    return binAt(this.#bins, this._ball.x)?.id;
  }

  protected reset(): void {
    this.#bins = layoutBins(sharesOf(this.segments));
    this._ball = START_BALL;
    this._lit = NO_PEGS;
    this._winner = undefined;
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    const bin = this.#bins.find((candidate) => candidate.id === id);
    if (!bin) {
      return;
    }
    this.reset();
    const points = buildPath(bin, this.random);
    const durations = stepDurations(points, this.random);
    const end = points.at(-1) ?? landingPoint(bin, PLINKO_HALF);
    const total = durations.reduce((sum, duration) => sum + duration, 0);
    this.#segment = -1;
    await token.frames(total, (progress) => {
      this.#fall(points, positionAt(points, durations, progress * total), token);
    });
    await token.frames(PLINKO_BOUNCE_MS, (progress) => {
      const hop =
        PLINKO_BOUNCE_HEIGHT *
        (1 - progress) *
        Math.abs(Math.sin(progress * Math.PI * PLINKO_BOUNCE_COUNT));
      this._ball = { x: end.x, y: end.y - hop };
    });
    if (!token.dead) {
      this._ball = end;
      this._winner = id;
    }
  }

  protected settle(id: string): void {
    const bin = this.#bins.find((candidate) => candidate.id === id);
    if (bin) {
      this._ball = landingPoint(bin, this.random());
      this._winner = id;
    }
  }

  protected override render(): TemplateResult {
    return html`
      <svg
        viewBox="0 0 ${numberText(PLINKO_VIEW_WIDTH)} ${numberText(PLINKO_VIEW_HEIGHT)}"
        role="img"
        aria-label=${this.label}
      >
        ${this.#bins.map((bin) => this.#bin(bin))} ${this.#separators()}
        ${PEGS.map(
          (peg) =>
            svg`<circle class=${this._lit.has(peg.key) ? 'peg lit' : 'peg'} cx=${peg.x} cy=${peg.y} r=${PLINKO_PEG_RADIUS}></circle>`,
        )}
        <circle
          class="ball"
          cx=${this._ball.x}
          cy=${this._ball.y}
          r=${PLINKO_BALL_RADIUS}
          stroke-width=${PLINKO_BALL_STROKE}
        ></circle>
      </svg>
    `;
  }

  /** Setzt die Kugel und lässt jeden Stift leuchten, den sie seit dem letzten Bild erreicht hat. */
  #fall(points: readonly PathPoint[], ball: BallState, token: MotionToken): void {
    this._ball = ball;
    for (let segment = this.#segment + 1; segment <= ball.segment; segment++) {
      const key = points[segment]?.peg;
      if (key !== undefined) {
        this.#glow(key, token);
      }
    }
    this.#segment = ball.segment;
  }

  #glow(key: string, token: MotionToken): void {
    this._lit = new Set([...this._lit, key]);
    void token.sleep(PLINKO_GLOW_MS).then(() => {
      this._lit = new Set([...this._lit].filter((lit) => lit !== key));
    });
  }

  #bin(bin: Bin): TemplateResult {
    const width = bin.x1 - bin.x0;
    const centre = width * PLINKO_HALF;
    const winner = bin.id === this._winner;
    return svg`<svg class=${winner ? PLINKO_WIN_CLASS : ''} x=${bin.x0} y=${PLINKO_BIN_TOP} width=${width} height=${PLINKO_BIN_HEIGHT}>
      <rect class="bin" x="0" y="0" width=${width} height=${PLINKO_BIN_HEIGHT} fill=${bin.color || FALLBACK_COLOR}></rect>
      ${width >= PLINKO_MIN_NAME_WIDTH ? svg`<text class="name" x=${centre} y=${PLINKO_NAME_Y}>${bin.label}</text>` : nothing}
      ${width >= PLINKO_MIN_CHANCE_WIDTH ? svg`<text class="chance" x=${centre} y=${PLINKO_CHANCE_Y}>${formatPercent(bin.share, this.language)}</text>` : nothing}
    </svg>`;
  }

  /** Trennwände an allen Fachgrenzen. */
  #separators(): TemplateResult[] {
    const edges = [PLINKO_BOARD_LEFT, ...this.#bins.map((bin) => bin.x1)];
    return edges.map(
      (x) =>
        svg`<line class="separator" x1=${x} x2=${x} y1=${PLINKO_BIN_TOP - PLINKO_SEPARATOR_RISE} y2=${PLINKO_BIN_TOP + PLINKO_BIN_HEIGHT} stroke-width=${PLINKO_SEPARATOR_WIDTH}></line>`,
    );
  }
}

defineOnce(STAGE_TAGS.plinko, TwPlinko);
