import { css, html, svg } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import {
  DRUM_BALL_STROKE,
  DRUM_CENTER_X,
  DRUM_CENTER_Y,
  DRUM_CHUTE_FROM,
  DRUM_CHUTE_WIDTH,
  DRUM_FALLBACK_LETTER,
  DRUM_HUB_RADIUS,
  DRUM_LEGEND_DOT,
  DRUM_LEGEND_TEXT_GAP,
  DRUM_LETTER_DROP,
  DRUM_LETTER_SIZE,
  DRUM_RADIUS,
  DRUM_RIB_WIDTH,
  DRUM_SHINE_OFFSET,
  DRUM_SHINE_OPACITY,
  DRUM_SHINE_SIZE,
  DRUM_TRAY_CORNER,
  DRUM_TRAY_DASH,
  DRUM_TRAY_LEFT,
  DRUM_TRAY_SIZE,
  DRUM_TRAY_TOP,
  DRUM_TRAY_X,
  DRUM_TRAY_Y,
  DRUM_VIEWBOX,
  DRUM_WALL_WIDTH,
  MS_PER_SECOND,
  STAGE_TAGS,
} from '../constants/index.ts';
import { DRUM_TOTAL_MS, DrumSimulation } from './drum-geometry.ts';
import { degreesOf, legendSlot, ribsPath, wallPath } from './drum-shapes.ts';
import type { Ball, Random } from './drum-balls.ts';
import { numberText } from './format.ts';
import type { MotionToken } from './motion.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import type { Share } from './stage-base.ts';
import { defineOnce } from './define.ts';
import { baseStyles, tokenStyles } from './styles.ts';

const WALL = wallPath();
const RIBS = ribsPath();
const CHUTE = `M${numberText(DRUM_CHUTE_FROM)} ${numberText(DRUM_CHUTE_FROM)} L${numberText(DRUM_TRAY_X)} ${numberText(DRUM_TRAY_Y)}`;

/** Lostrommel (SVG): drei Kugeln je Person, Kugelfläche ∝ Chance; die Gewinnerkugel rollt in die Ablage. */
export class TwDrum extends StageElement {
  static override properties = {
    ...StageElement.properties,
    random: { attribute: false },
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
      .drum {
        fill: var(--tw-color-fill);
      }
      .chute {
        fill: none;
        stroke: var(--tw-color-fill);
        stroke-linecap: round;
      }
      .tray {
        fill: none;
        stroke: var(--tw-color-rim);
        stroke-width: 3px;
      }
      .wall,
      .rib {
        fill: none;
        stroke: var(--tw-color-neutral);
        stroke-linecap: round;
      }
      .hub {
        fill: var(--tw-color-neutral);
      }
      .ball circle:first-child {
        stroke: var(--tw-color-surface);
      }
      .shine {
        fill: var(--tw-color-white);
      }
      .letter {
        fill: var(--tw-color-white);
        font-weight: 900;
        text-anchor: middle;
        pointer-events: none;
      }
      .legend {
        fill: var(--tw-color-text);
        font: 500 13px sans-serif;
      }
    `,
  ];

  /** Zufallsquelle für Startlage, Stöße und die Wahl der Kugel im Segment (für Tests ersetzbar). */
  declare random: Random;

  #sim = new DrumSimulation([]);

  constructor() {
    super();
    this.random = Math.random;
  }

  /** Die Person, deren Kugel in der Ablage liegt; sonst `undefined`. */
  get landedId(): string | undefined {
    return this.#sim.landedId();
  }

  protected reset(): void {
    this.#sim = new DrumSimulation(sharesOf(this.segments), this.random);
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    this.#prepare(id);
    await token.frames(DRUM_TOTAL_MS, (progress, elapsed) => {
      this.#sim.advance(progress * DRUM_TOTAL_MS, elapsed / MS_PER_SECOND);
      this.requestUpdate();
    });
    if (!token.dead) {
      this.#sim.finish();
      this.requestUpdate();
    }
  }

  protected settle(id: string): void {
    this.#prepare(id);
    this.#sim.finish();
    this.requestUpdate();
  }

  /** Beginnt mit frisch gemischten Kugeln; die Gewinnerkugel steht fest, bevor sich etwas bewegt. */
  #prepare(id: string): void {
    this.reset();
    this.#sim.choose(id, this.random());
  }

  protected override render(): TemplateResult {
    const centre = `${numberText(DRUM_CENTER_X)} ${numberText(DRUM_CENTER_Y)}`;
    const landed = this.#sim.landedId();
    const shares = sharesOf(this.segments);
    return html`
      <svg
        viewBox="0 0 ${DRUM_VIEWBOX} ${DRUM_VIEWBOX}"
        role="img"
        aria-label=${this.label}
        data-landed=${landed ?? ''}
      >
        <path class="chute" d=${CHUTE} stroke-width=${DRUM_CHUTE_WIDTH}></path>
        <rect
          class="tray"
          x=${DRUM_TRAY_LEFT}
          y=${DRUM_TRAY_TOP}
          width=${DRUM_TRAY_SIZE}
          height=${DRUM_TRAY_SIZE}
          rx=${DRUM_TRAY_CORNER}
          stroke-dasharray=${DRUM_TRAY_DASH}
        ></rect>
        <circle class="drum" cx=${DRUM_CENTER_X} cy=${DRUM_CENTER_Y} r=${DRUM_RADIUS}></circle>
        <path class="wall" d=${WALL} stroke-width=${DRUM_WALL_WIDTH}></path>
        <g transform="rotate(${numberText(degreesOf(this.#sim.angle))} ${centre})">
          <path class="rib" d=${RIBS} stroke-width=${DRUM_RIB_WIDTH}></path>
          <circle class="hub" cx=${DRUM_CENTER_X} cy=${DRUM_CENTER_Y} r=${DRUM_HUB_RADIUS}></circle>
        </g>
        ${this.#sim.balls.map((ball) => this.#ball(ball))}
        ${repeat(
          shares,
          (share) => share.id,
          (share, index) => this.#legend(share, index, shares.length),
        )}
      </svg>
    `;
  }

  #ball(ball: Ball): TemplateResult {
    const move = `translate(${numberText(ball.x)} ${numberText(ball.y)}) scale(${numberText(ball.scale)})`;
    const shine = numberText(-ball.r * DRUM_SHINE_OFFSET);
    const letter = Array.from(ball.label)[0] ?? DRUM_FALLBACK_LETTER;
    return svg`<g class="ball" data-id=${ball.id} data-out=${String(ball.out)} transform=${move}>
      <circle r=${ball.r} fill=${ball.color} stroke-width=${DRUM_BALL_STROKE}></circle>
      <circle class="shine" cx=${shine} cy=${shine} r=${ball.r * DRUM_SHINE_SIZE} opacity=${DRUM_SHINE_OPACITY}></circle>
      <text class="letter" y=${ball.r * DRUM_LETTER_DROP} font-size=${ball.r * DRUM_LETTER_SIZE}>${letter}</text>
    </g>`;
  }

  #legend(share: Share, index: number, count: number): TemplateResult {
    const slot = legendSlot(index, count);
    return svg`<g class="entry" transform="translate(${numberText(slot.x)} ${numberText(slot.y)})">
      <circle cx=${DRUM_LEGEND_DOT} cy=${-DRUM_LEGEND_DOT} r=${DRUM_LEGEND_DOT} fill=${share.color}></circle>
      <text class="legend" x=${DRUM_LEGEND_TEXT_GAP}>${share.label}</text>
    </g>`;
  }
}

defineOnce(STAGE_TAGS.drum, TwDrum);
