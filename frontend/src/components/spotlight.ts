import { css, html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { styleMap } from 'lit/directives/style-map.js';

import {
  EMPTY_TEXT,
  PERCENT,
  SPOTLIGHT_FALLBACK_COLOR,
  SPOTLIGHT_HEIGHT,
  SPOTLIGHT_HOLD_MS,
  SPOTLIGHT_WIDTH,
  STAGE_TAGS,
} from '../constants/index.ts';
import { numberText, percentText } from './format.ts';
import type { MotionToken } from './motion.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import { defineOnce } from './define.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { layoutTiles, spotlightDelay, spotlightSequence } from './spotlight-geometry.ts';
import type { Random, Tile } from './spotlight-geometry.ts';

const FLOOR = { x: 0, y: 0, w: SPOTLIGHT_WIDTH, h: SPOTLIGHT_HEIGHT };

const percentOf = (value: number, whole: number): string =>
  `${numberText((value / whole) * PERCENT)}%`;

/** Scheinwerfer: Kacheln als Treemap (Fläche ∝ Chance); ein Licht springt über sie und bleibt auf dem Gewinner. */
export class TwSpotlight extends StageElement {
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
      .tiles {
        position: relative;
        width: 100%;
        aspect-ratio: ${SPOTLIGHT_WIDTH} / ${SPOTLIGHT_HEIGHT};
        background: #0a1624;
        border-radius: 12px;
        overflow: hidden;
      }
      .tile {
        position: absolute;
        padding: 3px;
        box-sizing: border-box;
        container-type: size;
      }
      .face {
        position: relative;
        width: 100%;
        height: 100%;
        border-radius: 10px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        color: #ffffff;
        overflow: hidden;
        filter: brightness(0.42) saturate(0.65);
        transition:
          filter 0.12s,
          box-shadow 0.12s,
          transform 0.12s;
      }
      .name {
        font-size: clamp(14px, 24cqmin, 30px);
        font-weight: 900;
        overflow-wrap: anywhere;
        text-align: center;
      }
      .chance {
        font-size: clamp(12px, 13cqmin, 17px);
        font-weight: 500;
      }
      .tile.on {
        z-index: 2;
      }
      .on .face {
        filter: brightness(1.12) saturate(1.1);
        box-shadow:
          0 0 0 4px #ffffff,
          0 0 34px 8px rgba(255, 255, 255, 0.55);
        transform: scale(1.03);
      }
      .final .face {
        box-shadow:
          0 0 0 5px var(--tw-color-rim),
          0 0 40px 10px rgba(245, 197, 66, 0.7);
      }
      .lose .face {
        filter: brightness(0.3) saturate(0.5);
      }
      .still .face {
        transition: none;
      }
      @media (prefers-reduced-motion: reduce) {
        .face {
          transition: none;
        }
      }
    `,
  ];

  /** Zufallsquelle für die Folge der Sprünge (für Tests ersetzbar). */
  declare random: Random;

  #tiles: readonly Tile[] = [];
  #lit: string | undefined;
  #landed: string | undefined;
  #still = false;

  constructor() {
    super();
    this.random = Math.random;
  }

  /** Die Kachel, auf der der Scheinwerfer steht; sonst `undefined`. */
  get landedId(): string | undefined {
    return this.#landed;
  }

  protected reset(): void {
    this.#tiles = layoutTiles(sharesOf(this.segments), FLOOR);
    this.#clear(false);
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    this.#clear(false);
    const ids = this.#tiles.map((tile) => tile.id);
    const sequence = spotlightSequence(ids, id, this.random);
    for (const [index, tile] of sequence.entries()) {
      if (token.dead) {
        return;
      }
      this.#lit = tile;
      this.requestUpdate();
      await token.sleep(spotlightDelay(index, sequence.length));
    }
    if (token.dead) {
      return;
    }
    this.#land(id);
    await token.sleep(SPOTLIGHT_HOLD_MS);
  }

  protected settle(id: string): void {
    this.#clear(true);
    this.#land(id);
  }

  #clear(still: boolean): void {
    this.#lit = undefined;
    this.#landed = undefined;
    this.#still = still;
  }

  #land(id: string): void {
    this.#lit = id;
    this.#landed = id;
    this.requestUpdate();
  }

  protected override render(): TemplateResult {
    return html`
      <div
        class="tiles ${this.#still ? 'still' : EMPTY_TEXT}"
        role="img"
        aria-label=${this.label}
        data-landed=${this.#landed ?? EMPTY_TEXT}
      >
        ${repeat(
          this.#tiles,
          (tile) => tile.id,
          (tile) => this.#tile(tile),
        )}
      </div>
    `;
  }

  #tile(tile: Tile): TemplateResult {
    const place = styleMap({
      left: percentOf(tile.x, SPOTLIGHT_WIDTH),
      top: percentOf(tile.y, SPOTLIGHT_HEIGHT),
      width: percentOf(tile.w, SPOTLIGHT_WIDTH),
      height: percentOf(tile.h, SPOTLIGHT_HEIGHT),
    });
    const face = styleMap({ background: tile.color || SPOTLIGHT_FALLBACK_COLOR });
    const state = [
      tile.id === this.#lit ? 'on' : EMPTY_TEXT,
      tile.id === this.#landed ? 'final' : EMPTY_TEXT,
      this.#landed !== undefined && tile.id !== this.#landed ? 'lose' : EMPTY_TEXT,
    ].join(' ');
    return html`<div class="tile ${state}" data-id=${tile.id} style=${place}>
      <div class="face" style=${face}>
        <span class="name">${tile.label}</span>
        <span class="chance">${percentText(tile.share)}</span>
      </div>
    </div>`;
  }
}

defineOnce(STAGE_TAGS.spotlight, TwSpotlight);
