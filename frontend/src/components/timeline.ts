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
      .blocked {
        background: var(--tw-color-divider);
      }
      .tolerance {
        background: color-mix(in srgb, var(--tw-color-primary) 40%, transparent);
      }
      .free {
        background: var(--tw-color-primary);
      }
      .scale {
        display: flex;
        justify-content: space-between;
        font-size: 0.8em;
        color: var(--tw-color-text-muted);
        margin-top: 4px;
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

  protected override render(): TemplateResult {
    const span = Math.max(1, this.days + this.tolerance);
    const share = (days: number): string => `flex:${String(Math.max(0, days) / span)}`;
    const earliest = Math.max(0, this.days - this.tolerance);
    return html`
      <span class="label">${translate('frequency.timeline', this.language)}</span>
      <div class="bar" role="img" aria-label=${translate('frequency.timeline', this.language)}>
        <span class="blocked" style=${share(earliest)}></span>
        <span class="tolerance" style=${share(Math.min(this.tolerance, this.days))}></span>
        <span class="free" style=${share(span - this.days)}></span>
      </div>
      <div class="scale">
        <span>${translate('timeline.day', this.language)} 0</span>
        <span>${translate('timeline.earliest', this.language)}: ${earliest}</span>
        <span>${this.days}</span>
      </div>
    `;
  }
}

customElements.define(FORM_TAGS.timeline, TwTimeline);
