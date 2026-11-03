import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { FORM_TAGS, WEEKDAYS, WEEKDAY_COUNT } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { WEEKDAY_TEXT } from './options.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Anwesenheit in Wochenzeilen (Montag bis Sonntag); `present` enthält einen Wert je Tag. */
export class TwWeekPreview extends LitElement {
  static override properties = { present: { attribute: false }, language: { type: String } };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .grid {
        display: grid;
        grid-template-columns: repeat(7, minmax(0, 1fr));
        gap: 4px;
        max-width: 320px;
      }
      .head {
        font-size: 0.75em;
        color: var(--tw-color-text-muted);
        text-align: center;
      }
      .day {
        height: 24px;
        border-radius: 6px;
        background: var(--tw-color-primary);
      }
      .day.absent {
        background: repeating-linear-gradient(
          45deg,
          var(--tw-color-divider),
          var(--tw-color-divider) 4px,
          transparent 4px,
          transparent 8px
        );
      }
    `,
  ];

  declare present: readonly boolean[];
  declare language: string;

  constructor() {
    super();
    this.present = [];
    this.language = '';
  }

  protected override render(): TemplateResult {
    const text = (key: Parameters<typeof translate>[0]): string => translate(key, this.language);
    return html`
      <span class="label">${text('preview.title')}</span>
      <div class="grid" role="img" aria-label=${text('preview.title')}>
        ${WEEKDAYS.map((day) => html`<span class="head">${text(WEEKDAY_TEXT[day])}</span>`)}
        ${repeat(
          this.present,
          (_, index) => index,
          (isPresent, index) => html`
            <span
              class=${isPresent ? 'day' : 'day absent'}
              title=${`${text('preview.week')} ${String(Math.floor(index / WEEKDAY_COUNT) + 1)}: ${text(isPresent ? 'preview.present' : 'preview.absent')}`}
            ></span>
          `,
        )}
      </div>
    `;
  }
}

customElements.define(FORM_TAGS.weekPreview, TwWeekPreview);
