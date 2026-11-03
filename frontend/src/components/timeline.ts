import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_TAGS } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Zeitstrahl eines festen Intervalls: gesperrt, Toleranz und frei, in Tagen nach der letzten Zuteilung. */
export class TwTimeline extends LitElement {
  static override properties = {
    days: { type: Number },
    tolerance: { type: Number },
    language: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .bar {
        display: flex;
        height: 16px;
        border-radius: 8px;
        overflow: hidden;
      }
      .outside {
        background: color-mix(in srgb, var(--tw-color-primary) 30%, transparent);
      }
      .window {
        background: var(--tw-color-primary);
      }
      .marks {
        position: relative;
        height: 1.4em;
        font-size: 0.8em;
        color: var(--tw-color-text-muted);
      }
      .marks span {
        position: absolute;
        white-space: nowrap;
      }
      .target {
        left: calc(var(--at) * 100%);
        translate: -50% 0;
      }
      .earliest {
        right: calc((1 - var(--at)) * 100%);
      }
      .latest {
        left: calc(var(--at) * 100%);
      }
    `,
  ];

  declare days: number;
  declare tolerance: number;
  declare language: string;

  constructor() {
    super();
    this.days = 1;
    this.tolerance = 0;
    this.language = '';
  }

  /** Zeitachse: Anfang, Toleranzfenster und Ende; hinter dem Fenster bleibt ein Stück Skala. */
  #axis(): { earliest: number; latest: number; total: number } {
    const earliest = Math.max(0, this.days - this.tolerance);
    const latest = this.days + this.tolerance;
    return { earliest, latest, total: latest + Math.max(1, this.tolerance) };
  }

  protected override render(): TemplateResult {
    const { earliest, latest, total } = this.#axis();
    const at = (day: number): string => `--at:${String(day / total)}`;
    const share = (days: number): string => `flex:${String(days / total)}`;
    return html`
      <span class="label">${translate('frequency.timeline', this.language)}</span>
      <div class="marks">
        <span class="target" style=${at(this.days)}>${this.days}</span>
      </div>
      <div class="bar" role="img" aria-label=${translate('frequency.timeline', this.language)}>
        <span class="outside" style=${share(earliest)}></span>
        <span class="window" style=${share(latest - earliest)}></span>
        <span class="outside" style=${share(total - latest)}></span>
      </div>
      <div class="marks">
        <span class="earliest" style=${at(earliest)}
          >${translate('timeline.earliest', this.language)}: ${earliest}</span
        >
        <span class="latest" style=${at(latest)}
          >${translate('timeline.latest', this.language)}: ${latest}</span
        >
      </div>
    `;
  }
}

customElements.define(FORM_TAGS.timeline, TwTimeline);
