import { css, html } from 'lit';
import type { TemplateResult } from 'lit';

import {
  EMPTY_TEXT,
  NEWS_DECOYS,
  NEWS_END_HOLD_MS,
  NEWS_FINAL_IN_MS,
  NEWS_HOLD_MS,
  NEWS_IN_MS,
  NEWS_OUT_MS,
  NEWS_STAMP_MS,
  STAGE_TAGS,
} from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { decoysOf } from './decoys.ts';
import { defineOnce } from './define.ts';
import type { MotionToken } from './motion.ts';
import { StageElement, sharesOf } from './stage-base.ts';
import type { Share } from './stage-base.ts';
import type { Random } from './spotlight-geometry.ts';
import { baseStyles, tokenStyles } from './styles.ts';

type Phase = 'idle' | 'in' | 'out' | 'final' | 'still';

interface Page {
  readonly headline: string;
  readonly sub: string;
  readonly color: string;
}

/** Eilmeldung: Zeitungen mit Gerüchten wirbeln herein und fort, zuletzt die Titelseite mit Stempel. */
export class TwNews extends StageElement {
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
      .frame {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
      }
      .paper {
        position: relative;
        box-sizing: border-box;
        width: min(100%, 300px);
        padding: 16px 18px 22px;
        border-radius: 6px;
        background: #f6f1e3;
        color: #1f2328;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
        font-family: Georgia, serif;
      }
      .mast {
        text-align: center;
        font-size: 1.4em;
        font-weight: 900;
        letter-spacing: 0.08em;
      }
      .rule {
        height: 3px;
        margin: 4px 0 10px;
        background: #1f2328;
        box-shadow: 0 4px 0 #1f2328;
      }
      .head {
        color: var(--tw-page-color);
        font-size: 1.5em;
        font-weight: 900;
        line-height: 1.15;
        overflow-wrap: anywhere;
      }
      .sub {
        margin-top: 8px;
        color: #5a616b;
        font-family: inherit;
        font-size: 0.8em;
      }
      .lines {
        display: flex;
        flex-direction: column;
        gap: 5px;
        margin-top: 12px;
      }
      .lines i {
        display: block;
        height: 5px;
        border-radius: 2px;
        background: #d9d2bd;
      }
      .stamp {
        position: absolute;
        right: 10px;
        bottom: 10px;
        padding: 0 8px;
        border: 4px solid #d32f2f;
        border-radius: 6px;
        color: #d32f2f;
        font-family: Roboto, system-ui, sans-serif;
        font-size: 1.4em;
        font-weight: 900;
        opacity: 0;
        transform: rotate(-14deg) scale(2.2);
        transition:
          transform var(--tw-stamp) ease-in,
          opacity var(--tw-stamp);
      }
      .stamped .stamp {
        opacity: 1;
        transform: rotate(-14deg) scale(1);
      }
      .in,
      .final {
        animation: tw-news-in var(--tw-in) ease-out both;
      }
      .out {
        animation: tw-news-out var(--tw-out) ease-in both;
      }
      @keyframes tw-news-in {
        from {
          opacity: 0;
          transform: translateY(40px) rotate(720deg) scale(0.2);
        }
        to {
          opacity: 1;
          transform: none;
        }
      }
      @keyframes tw-news-out {
        to {
          opacity: 0;
          transform: translateY(160px) rotate(-90deg) scale(0.2);
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .paper,
        .stamp {
          animation: none;
          transition: none;
        }
      }
    `,
  ];

  /** Zufallsquelle für die Auswahl der Gerüchte (für Tests ersetzbar). */
  declare random: Random;

  #phase: Phase = 'idle';
  #page: Page | undefined;
  #stamped = false;

  constructor() {
    super();
    this.random = Math.random;
  }

  /** Ob die Titelseite mit dem Gewinner und dem Stempel steht. */
  get stamped(): boolean {
    return this.#stamped;
  }

  protected reset(): void {
    this.#phase = 'idle';
    this.#page = undefined;
    this.#stamped = false;
  }

  protected async play(id: string, token: MotionToken): Promise<void> {
    const shares = sharesOf(this.segments);
    const byId = new Map(shares.map((share) => [share.id, share]));
    const winner = byId.get(id);
    this.reset();
    const decoys = decoysOf(
      shares.map((share) => share.id),
      id,
      NEWS_DECOYS,
      this.random,
    );
    for (const decoy of decoys) {
      const share = byId.get(decoy);
      if (!share) {
        continue;
      }
      await this.#show('in', this.#rumor(share), NEWS_IN_MS + NEWS_HOLD_MS, token);
      await this.#show('out', this.#page, NEWS_OUT_MS, token);
    }
    if (winner) {
      await this.#show('final', this.#extra(winner), NEWS_FINAL_IN_MS, token);
      this.#stamped = true;
      this.requestUpdate();
      await token.sleep(NEWS_STAMP_MS + NEWS_END_HOLD_MS);
    }
  }

  protected settle(id: string): void {
    const winner = sharesOf(this.segments).find((share) => share.id === id);
    this.#phase = 'still';
    this.#page = winner ? this.#extra(winner) : undefined;
    this.#stamped = winner !== undefined;
    this.requestUpdate();
  }

  async #show(phase: Phase, page: Page | undefined, ms: number, token: MotionToken): Promise<void> {
    this.#phase = phase;
    this.#page = page;
    this.requestUpdate();
    await token.sleep(ms);
  }

  #text(key: TextKey, params?: Record<string, string>): string {
    return translate(key, this.language, params);
  }

  #rumor(share: Share): Page {
    return {
      headline: this.#text('news.rumor', { name: share.label }),
      sub: this.#text('news.rumor.sub'),
      color: share.color,
    };
  }

  #extra(share: Share): Page {
    return {
      headline: this.#text('news.extra', { name: share.label, task: this.taskName }),
      sub: this.#text('news.extra.sub'),
      color: share.color,
    };
  }

  protected override render(): TemplateResult {
    const page = this.#page;
    const style = [
      `--tw-in:${String(this.#phase === 'final' ? NEWS_FINAL_IN_MS : NEWS_IN_MS)}ms`,
      `--tw-out:${String(NEWS_OUT_MS)}ms`,
      `--tw-stamp:${String(NEWS_STAMP_MS)}ms`,
      `--tw-page-color:${page?.color || 'inherit'}`,
    ].join(';');
    return html`
      <div class="frame">
        <div
          class="paper ${this.#phase} ${this.#stamped ? 'stamped' : EMPTY_TEXT}"
          style=${style}
          role="img"
          aria-label=${this.label}
          data-stamped=${this.#stamped ? 'true' : 'false'}
        >
          <div class="mast">${this.#text('news.masthead')}</div>
          <div class="rule"></div>
          <div class="head">${page?.headline ?? this.#text('news.ready')}</div>
          <div class="sub">${page?.sub ?? EMPTY_TEXT}</div>
          <div class="lines"><i></i><i></i><i></i></div>
          <div class="stamp">${this.#text('news.stamp')}</div>
        </div>
      </div>
    `;
  }
}

defineOnce(STAGE_TAGS.news, TwNews);
