import { css, html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { styleMap } from 'lit/directives/style-map.js';

import {
  EMPTY_TEXT,
  FALLBACK_COLOR,
  OSCAR_CARD_MS,
  OSCAR_CURTAIN_MS,
  OSCAR_ENVELOPE_MS,
  OSCAR_FLAP_MS,
  OSCAR_HOLD_MS,
  OSCAR_LOSER_OPACITY,
  OSCAR_NOMINEE_MIN_MS,
  OSCAR_NOMINEE_TOTAL_MS,
  OSCAR_PAUSE_MS,
  STAGE_TAGS,
} from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import './confetti.ts';
import { defineOnce } from './define.ts';
import type { MotionToken } from './motion.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import type { Share } from './stage-base.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Die Abschnitte der Verleihung in ihrer Reihenfolge; ein Abschnitt gilt auch in allen folgenden. */
const PHASES = ['closed', 'open', 'nominees', 'envelope', 'flap', 'card', 'win'] as const;
type Phase = (typeof PHASES)[number];

/** Oscar-Verleihung: Vorhang auf, Scheinwerfer über die Nominierten, Umschlag, Verkündung mit Konfetti. */
export class TwOscar extends StageElement {
  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: block;
        width: 100%;
        height: 100%;
      }
      .scene {
        position: relative;
        width: 100%;
        height: 100%;
        overflow: hidden;
        border-radius: 12px;
        background: #0a1624;
        color: #ffffff;
        container-type: size;
      }
      .floor {
        position: absolute;
        inset: auto 0 0;
        height: 14%;
        background: #7a1626;
      }
      .nominees {
        position: absolute;
        inset: 8% 4% auto;
        display: flex;
        justify-content: center;
        gap: 3%;
      }
      .nominee {
        flex: 0 1 22%;
        min-width: 0;
        text-align: center;
        font-size: clamp(11px, 4cqw, 15px);
        transition:
          transform 0.12s,
          opacity 0.3s;
      }
      .face {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 70%;
        aspect-ratio: 1;
        margin: 0 auto 4px;
        border: 3px solid #ffffff;
        border-radius: 50%;
        font-size: 1.6em;
        font-weight: 900;
      }
      .nominee.lit {
        transform: scale(1.18);
      }
      .nominee.lit .face {
        box-shadow: 0 0 24px 6px rgba(255, 236, 170, 0.7);
      }
      .nominee.lose {
        opacity: var(--tw-lose-opacity);
      }
      .nominee b {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .curtain {
        position: absolute;
        top: 0;
        bottom: 14%;
        width: 50%;
        background: repeating-linear-gradient(
          90deg,
          #6d1220 0 10px,
          #b3263b 10px 22px,
          #6d1220 22px 32px
        );
        transition: transform var(--tw-curtain) ease-in-out;
      }
      .curtain.left {
        left: 0;
      }
      .curtain.right {
        right: 0;
      }
      .at-open .curtain.left {
        transform: translateX(-80%);
      }
      .at-open .curtain.right {
        transform: translateX(80%);
      }
      .envelope {
        position: absolute;
        left: 50%;
        bottom: 18%;
        width: 46%;
        aspect-ratio: 2 / 1;
        transform: translate(-50%, 220%);
        transition: transform var(--tw-envelope) ease-out;
      }
      .at-envelope .envelope {
        transform: translate(-50%, 0);
      }
      .body {
        position: absolute;
        inset: 0;
        border: 2px solid #bda76d;
        border-radius: 6px;
        background: #e7d9b8;
      }
      .pocket {
        position: absolute;
        z-index: 2;
        inset: auto 0 0;
        height: 62%;
        border: 2px solid #bda76d;
        border-radius: 0 0 6px 6px;
        background: #e7d9b8;
      }
      .flap {
        position: absolute;
        inset: 0 0 auto;
        height: 55%;
        border: 2px solid #bda76d;
        background: #f1e6c6;
        clip-path: polygon(0 0, 100% 0, 50% 100%);
        z-index: 3;
        transform-origin: top;
        transition: transform var(--tw-flap);
      }
      .at-flap .flap {
        transform: rotateX(180deg);
        z-index: 0;
      }
      .card {
        position: absolute;
        z-index: 1;
        inset: 8% 8% 14%;
        display: flex;
        align-items: flex-start;
        padding-top: 6%;
        justify-content: center;
        border: 3px solid #f5c542;
        border-radius: 6px;
        background: #fffaf0;
        color: #8a6d00;
        font-size: clamp(10px, 3.4cqw, 14px);
        font-weight: 700;
        text-align: center;
        transform: none;
        opacity: 0;
        transition:
          transform var(--tw-card),
          opacity var(--tw-card);
      }
      .at-flap .card {
        opacity: 1;
      }
      .at-card .card {
        transform: translateY(-75%);
      }
      .award {
        position: absolute;
        inset: 40% 6% auto;
        padding: 4% 3%;
        border: 4px solid #f5c542;
        border-radius: 14px;
        background: #fffaf0;
        color: #1f2328;
        text-align: center;
        opacity: 0;
        pointer-events: none;
        box-shadow: 0 0 40px 10px rgba(245, 197, 66, 0.6);
      }
      .at-win .award {
        opacity: 1;
      }
      .at-win .envelope {
        opacity: 0;
      }
      .award .what {
        color: #8a6d00;
        font-size: clamp(11px, 4cqw, 16px);
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .award .who {
        font-size: clamp(22px, 11cqw, 44px);
        font-weight: 900;
        overflow-wrap: anywhere;
      }
      .still * {
        transition: none;
      }
      @media (prefers-reduced-motion: reduce) {
        * {
          transition: none;
        }
      }
    `,
  ];

  #phase: Phase = 'closed';
  #winner: string | undefined;
  #lit: string | undefined;
  #still = false;

  /** Der Abschnitt der Verleihung, in dem die Bühne gerade ist. */
  get phase(): Phase {
    return this.#phase;
  }

  protected reset(): void {
    this.#phase = 'closed';
    this.#winner = undefined;
    this.#lit = undefined;
    this.#still = false;
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    this.reset();
    const dwell = Math.max(
      OSCAR_NOMINEE_MIN_MS,
      OSCAR_NOMINEE_TOTAL_MS / Math.max(this.segments.length, 1),
    );
    await this.#enter('open', OSCAR_CURTAIN_MS, token);
    this.#phase = 'nominees';
    for (const share of sharesOf(this.segments)) {
      this.#lit = share.id;
      this.requestUpdate();
      await token.sleep(dwell);
    }
    this.#lit = undefined;
    await this.#enter('envelope', OSCAR_ENVELOPE_MS, token);
    await this.#enter('flap', OSCAR_FLAP_MS, token);
    await this.#enter('card', OSCAR_CARD_MS + OSCAR_PAUSE_MS, token);
    this.#winner = id;
    await this.#enter('win', OSCAR_HOLD_MS, token);
  }

  protected settle(id: string): void {
    this.#winner = id;
    this.#phase = 'win';
    this.#lit = undefined;
    this.#still = true;
    this.requestUpdate();
  }

  async #enter(phase: Phase, ms: number, token: MotionToken): Promise<void> {
    this.#phase = phase;
    this.requestUpdate();
    await token.sleep(ms);
  }

  #text(key: TextKey, params?: Record<string, string>): string {
    return translate(key, this.language, params);
  }

  protected override render(): TemplateResult {
    const shares = sharesOf(this.segments);
    const winner = shares.find((share) => share.id === this.#winner);
    const reached = PHASES.slice(0, PHASES.indexOf(this.#phase) + 1).map((phase) => `at-${phase}`);
    const style = styleMap({
      '--tw-curtain': `${String(OSCAR_CURTAIN_MS)}ms`,
      '--tw-envelope': `${String(OSCAR_ENVELOPE_MS)}ms`,
      '--tw-flap': `${String(OSCAR_FLAP_MS)}ms`,
      '--tw-card': `${String(OSCAR_CARD_MS)}ms`,
      '--tw-lose-opacity': String(OSCAR_LOSER_OPACITY),
    });
    return html`
      <div
        class="scene ${reached.join(' ')} ${this.#still ? 'still' : EMPTY_TEXT}"
        style=${style}
        role="img"
        aria-label=${this.label}
        data-phase=${this.#phase}
        data-winner=${this.#winner ?? EMPTY_TEXT}
      >
        <div class="floor"></div>
        <div class="nominees">
          ${repeat(
            shares,
            (share) => share.id,
            (share) => this.#nominee(share, winner),
          )}
        </div>
        <div class="envelope">
          <div class="body"></div>
          <div class="card">${this.#text('oscar.envelope')}</div>
          <div class="pocket"></div>
          <div class="flap"></div>
        </div>
        ${winner ? this.#award(winner) : EMPTY_TEXT}
        ${this.#phase === 'win' && !this.#still ? html`<tw-confetti></tw-confetti>` : EMPTY_TEXT}
        <div class="curtain left"></div>
        <div class="curtain right"></div>
      </div>
    `;
  }

  #nominee(share: Share, winner: Share | undefined): TemplateResult {
    const state = [
      share.id === this.#lit ? 'lit' : EMPTY_TEXT,
      winner && winner.id !== share.id ? 'lose' : EMPTY_TEXT,
    ].join(' ');
    return html`<div class="nominee ${state}" data-id=${share.id}>
      <div class="face" style="background:${share.color || FALLBACK_COLOR}">
        ${share.label.slice(0, 1)}
      </div>
      <b>${share.label}</b>
    </div>`;
  }

  #award(winner: Share): TemplateResult {
    return html`<div class="award">
      <div class="what">${this.#text('oscar.award', { task: this.taskName })}</div>
      <div class="who" style="color:${winner.color || FALLBACK_COLOR}">${winner.label}</div>
    </div>`;
  }
}

defineOnce(STAGE_TAGS.oscar, TwOscar);
