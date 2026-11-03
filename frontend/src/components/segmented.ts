import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { emitChange } from './change.ts';
import { FORM_TAGS } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { formStyles } from './formStyles.ts';

export interface SegmentOption {
  readonly id: string;
  readonly label: string;
}

/** Umschalter für genau eine Wahl (Radiogruppe als Segmentleiste). */
export class TwSegmented extends LitElement {
  static override properties = {
    label: { type: String },
    options: { attribute: false },
    value: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .bar {
        display: inline-flex;
        flex-wrap: wrap;
        border: 1px solid var(--tw-color-divider);
        border-radius: 8px;
        overflow: hidden;
      }
      button {
        min-height: 36px;
        padding: 0 14px;
        border: 0;
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      button[aria-checked='true'] {
        background: var(--tw-color-primary);
        color: #fff;
      }
    `,
  ];

  declare label: string;
  declare options: readonly SegmentOption[];
  declare value: string;

  constructor() {
    super();
    this.label = '';
    this.options = [];
    this.value = '';
  }

  protected override render(): TemplateResult {
    return html`
      <span class="label">${this.label}</span>
      <div class="bar" role="radiogroup" aria-label=${this.label}>
        ${repeat(
          this.options,
          (option) => option.id,
          (option) => html`
            <button
              type="button"
              role="radio"
              aria-checked=${option.id === this.value ? 'true' : 'false'}
              @click=${() => {
                emitChange(this, option.id);
              }}
            >
              ${option.label}
            </button>
          `,
        )}
      </div>
    `;
  }
}

customElements.define(FORM_TAGS.segmented, TwSegmented);
