import { css, html, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { styleMap } from 'lit/directives/style-map.js';

import {
  EMPTY_TEXT,
  EVENT_STAGE_START,
  FALLBACK_COLOR,
  SCRATCH_BRUSH,
  SCRATCH_CANVAS_HEIGHT,
  SCRATCH_CANVAS_WIDTH,
  SCRATCH_CHECK_MS,
  SCRATCH_COIN_BRUSH,
  SCRATCH_COIN_MS,
  SCRATCH_COIN_START_MS,
  SCRATCH_COLORS,
  SCRATCH_FOIL_HEAD,
  SCRATCH_FOIL_HINT_FONT,
  SCRATCH_FOIL_HINT_Y,
  SCRATCH_FOIL_INK,
  SCRATCH_FOIL_NAME_FONT,
  SCRATCH_FOIL_NAME_Y,
  SCRATCH_FOIL_STOPS,
  SCRATCH_FOIL_WHITE,
  SCRATCH_HOLD_MS,
  SCRATCH_PAIR,
  SCRATCH_REVEAL_SHARE,
  STAGE_TAGS,
} from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { defineOnce } from './define.ts';
import type { MotionToken } from './motion.ts';
import { clearedShare, coinStroke, toCanvas } from './scratch-geometry.ts';
import type { Point } from './scratch-geometry.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import type { Share } from './stage-base.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/**
 * Rubbellose: ein Los je Person mit der Chance auf der Silberschicht. Man rubbelt selbst (Finger
 * oder Maus; das erste Rubbeln startet die Auslosung) oder lässt eine Münze das Gewinnerlos freilegen.
 * Das Ergebnis steht vorher fest; sobald das Gewinnerlos frei liegt, endet die Animation.
 */
export class TwScratch extends StageElement {
  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: block;
        width: 100%;
        height: 100%;
      }
      .frame {
        display: flex;
        flex-direction: column;
        justify-content: center;
        width: 100%;
        height: 100%;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
        gap: 10px;
      }
      .card {
        position: relative;
        height: 104px;
        overflow: hidden;
        border: 3px solid var(--tw-card-color);
        border-radius: 12px;
        background: var(--tw-color-white);
        color: var(--tw-color-ink);
        user-select: none;
      }
      .under {
        position: absolute;
        inset: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4px;
        text-align: center;
      }
      .under b {
        color: var(--tw-card-color);
        font-size: 1.15em;
        font-weight: 900;
        overflow-wrap: anywhere;
      }
      .under span {
        color: var(--tw-color-text-muted);
        font-size: 0.8em;
      }
      .card.win {
        border-color: var(--tw-color-rim);
        box-shadow:
          0 0 0 3px var(--tw-color-rim),
          0 0 26px var(--tw-glow-gold);
      }
      .card.win .under {
        background: linear-gradient(
          135deg,
          ${unsafeCSS(SCRATCH_COLORS.goldLight)},
          ${unsafeCSS(SCRATCH_COLORS.goldDark)}
        );
      }
      .card.lose {
        opacity: 0.55;
      }
      canvas {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        cursor: crosshair;
        touch-action: none;
        transition: opacity 0.3s;
      }
      canvas.gone {
        opacity: 0;
        pointer-events: none;
      }
      .hint {
        margin-top: 8px;
        color: var(--tw-color-text-muted);
        font-size: 0.8em;
        text-align: center;
      }
      @media (prefers-reduced-motion: reduce) {
        canvas {
          transition: none;
        }
      }
    `,
  ];

  /** Zählt bei jedem Zurücksetzen hoch, damit neue Lose frische Zeichenflächen bekommen. */
  #generation = 0;
  #winner: string | undefined;
  #opened = new Set<string>();
  #started = false;
  #touched = false;
  #finish: (() => void) | undefined;
  #last: Point | undefined;
  #lastCheck = 0;
  readonly #painted = new WeakSet<HTMLCanvasElement>();

  /** Die aufgedeckten Lose (frei gerubbelt). */
  get openedIds(): ReadonlySet<string> {
    return this.#opened;
  }

  protected reset(): void {
    this.#generation += 1;
    this.#winner = undefined;
    this.#opened = new Set();
    this.#started = false;
    this.#touched = false;
    this.#finish = undefined;
    this.#last = undefined;
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    this.#winner = id;
    this.requestUpdate();
    if (!this.#opened.has(id)) {
      if (this.#touched) {
        await new Promise<void>((resolve) => {
          this.#finish = resolve;
        });
        return;
      }
      await token.sleep(SCRATCH_COIN_START_MS);
      await this.#coin(id, token);
      this.#open(id);
    }
    await token.sleep(SCRATCH_HOLD_MS);
  }

  protected settle(id: string): void {
    this.#winner = id;
    this.#open(id);
  }

  async #coin(id: string, token: MotionToken): Promise<void> {
    const canvas = this.#canvasOf(id);
    if (!canvas) {
      return;
    }
    await token.frames(SCRATCH_COIN_MS, (progress) => {
      const { from, to } = coinStroke(progress);
      this.#stroke(canvas, from, to, SCRATCH_COIN_BRUSH);
    });
  }

  #canvasOf(id: string): HTMLCanvasElement | undefined {
    return [...(this.shadowRoot?.querySelectorAll('canvas') ?? [])].find(
      (canvas) => canvas.dataset['id'] === id,
    );
  }

  /** Ein Los gilt als aufgedeckt; ist es das Gewinnerlos, ist die Auslosung zu Ende. */
  #open(id: string): void {
    this.#opened = new Set([...this.#opened, id]);
    this.requestUpdate();
    if (id === this.#winner) {
      this.#finish?.();
      this.#finish = undefined;
    }
  }

  #stroke(canvas: HTMLCanvasElement, from: Point, to: Point, width: number): void {
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }
    context.globalCompositeOperation = 'destination-out';
    context.lineCap = 'round';
    context.lineWidth = width;
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
  }

  #point(event: PointerEvent, canvas: HTMLCanvasElement): Point {
    return toCanvas({ x: event.clientX, y: event.clientY }, canvas.getBoundingClientRect());
  }

  #onDown(event: PointerEvent, canvas: HTMLCanvasElement): void {
    this.#touched = true;
    this.#last = this.#point(event, canvas);
    canvas.setPointerCapture(event.pointerId);
    this.#stroke(canvas, this.#last, this.#last, SCRATCH_BRUSH);
    if (!this.#started) {
      this.#started = true;
      this.dispatchEvent(new CustomEvent(EVENT_STAGE_START, { bubbles: true, composed: true }));
    }
  }

  #onMove(event: PointerEvent, canvas: HTMLCanvasElement, id: string): void {
    if (!this.#last) {
      return;
    }
    const point = this.#point(event, canvas);
    this.#stroke(canvas, this.#last, point, SCRATCH_BRUSH);
    this.#last = point;
    if (event.timeStamp - this.#lastCheck >= SCRATCH_CHECK_MS) {
      this.#lastCheck = event.timeStamp;
      this.#measure(canvas, id);
    }
  }

  #onUp(canvas: HTMLCanvasElement, id: string): void {
    this.#last = undefined;
    this.#measure(canvas, id);
  }

  /** Ist genug Silber ab, gilt das Los als aufgedeckt. */
  #measure(canvas: HTMLCanvasElement, id: string): void {
    if (this.#opened.has(id)) {
      return;
    }
    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }
    const pixels = context.getImageData(0, 0, SCRATCH_CANVAS_WIDTH, SCRATCH_CANVAS_HEIGHT);
    if (clearedShare(pixels.data) >= SCRATCH_REVEAL_SHARE) {
      this.#open(id);
    }
  }

  #paintFoil(canvas: HTMLCanvasElement, share: Share): void {
    const context = canvas.getContext('2d', { willReadFrequently: true });
    if (!context) {
      return;
    }
    const gradient = context.createLinearGradient(
      0,
      0,
      SCRATCH_CANVAS_WIDTH,
      SCRATCH_CANVAS_HEIGHT,
    );
    for (const [stop, color] of SCRATCH_FOIL_STOPS) {
      gradient.addColorStop(stop, color);
    }
    const middle = SCRATCH_CANVAS_WIDTH / SCRATCH_PAIR;
    context.globalCompositeOperation = 'source-over';
    context.fillStyle = gradient;
    context.fillRect(0, 0, SCRATCH_CANVAS_WIDTH, SCRATCH_CANVAS_HEIGHT);
    context.fillStyle = share.color || FALLBACK_COLOR;
    context.fillRect(0, 0, SCRATCH_CANVAS_WIDTH, SCRATCH_FOIL_HEAD);
    context.textAlign = 'center';
    context.fillStyle = SCRATCH_FOIL_WHITE;
    context.font = SCRATCH_FOIL_NAME_FONT;
    context.fillText(share.label, middle, SCRATCH_FOIL_NAME_Y);
    context.fillStyle = SCRATCH_FOIL_INK;
    context.font = SCRATCH_FOIL_HINT_FONT;
    context.fillText(this.#text('scratch.foil.hint'), middle, SCRATCH_FOIL_HINT_Y);
  }

  protected override updated(): void {
    const shares = new Map(sharesOf(this.segments).map((share) => [share.id, share]));
    for (const canvas of this.shadowRoot?.querySelectorAll('canvas') ?? []) {
      const share = shares.get(canvas.dataset['id'] ?? EMPTY_TEXT);
      if (share && !this.#painted.has(canvas)) {
        this.#painted.add(canvas);
        this.#paintFoil(canvas, share);
      }
    }
  }

  #text(key: TextKey): string {
    return translate(key, this.language);
  }

  protected override render(): TemplateResult {
    return html`
      <div class="frame">
        <div class="grid" role="group" aria-label=${this.label}>
          ${repeat(
            sharesOf(this.segments),
            (share) => `${String(this.#generation)}:${share.id}`,
            (share) => this.#card(share),
          )}
        </div>
        <p class="hint">${this.#text('scratch.hint')}</p>
      </div>
    `;
  }

  /** Ob das Los gewonnen oder verloren hat; solange es zu ist oder der Gewinner fehlt, `undefined`. */
  #verdict(share: Share): 'win' | 'lose' | undefined {
    if (!this.#opened.has(share.id) || this.#winner === undefined) {
      return undefined;
    }
    return share.id === this.#winner ? 'win' : 'lose';
  }

  #verdictText(verdict: 'win' | 'lose' | undefined, suffix: string): string {
    return verdict ? this.#text(`scratch.${verdict}${suffix}` as TextKey) : EMPTY_TEXT;
  }

  #card(share: Share): TemplateResult {
    const opened = this.#opened.has(share.id);
    const verdict = this.#verdict(share);
    return html`
      <div
        class="card ${verdict ?? EMPTY_TEXT}"
        style=${styleMap({ '--tw-card-color': share.color || FALLBACK_COLOR })}
        data-id=${share.id}
      >
        <div class="under">
          <b>${this.#verdictText(verdict, EMPTY_TEXT)}</b>
          <span>${this.#verdictText(verdict, '.sub')}</span>
        </div>
        <canvas
          class=${opened ? 'gone' : EMPTY_TEXT}
          width=${SCRATCH_CANVAS_WIDTH}
          height=${SCRATCH_CANVAS_HEIGHT}
          data-id=${share.id}
          aria-hidden="true"
          @pointerdown=${(event: PointerEvent) => {
            this.#onDown(event, event.currentTarget as HTMLCanvasElement);
          }}
          @pointermove=${(event: PointerEvent) => {
            this.#onMove(event, event.currentTarget as HTMLCanvasElement, share.id);
          }}
          @pointerup=${(event: PointerEvent) => {
            this.#onUp(event.currentTarget as HTMLCanvasElement, share.id);
          }}
          @pointercancel=${(event: PointerEvent) => {
            this.#onUp(event.currentTarget as HTMLCanvasElement, share.id);
          }}
        ></canvas>
      </div>
    `;
  }
}

defineOnce(STAGE_TAGS.scratch, TwScratch);
