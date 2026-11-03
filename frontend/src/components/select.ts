import { LitElement, css, html } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import type { TemplateResult } from 'lit';

import { FORM_TAGS } from '../constants/index.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { emitChange } from './change.ts';
import { defineOnce } from './define.ts';

export interface SelectOption {
  readonly id: string;
  readonly label: string;
}

/** Dropdown für genau eine Wahl; bricht bei langen Beschriftungen nicht um (anders als der Segment-Umschalter). */
export class TwSelect extends LitElement {
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
      select {
        width: 100%;
        cursor: pointer;
      }
    `,
  ];

  declare label: string;
  declare options: readonly SelectOption[];
  declare value: string;

  constructor() {
    super();
    this.label = '';
    this.options = [];
    this.value = '';
  }

  protected override render(): TemplateResult {
    return html`
      <label>
        <span class="label">${this.label}</span>
        <select
          class="control"
          @change=${(event: Event) => {
            emitChange(this, (event.target as HTMLSelectElement).value);
          }}
        >
          ${repeat(
            this.options,
            (option) => option.id,
            (option) =>
              html`<option value=${option.id} ?selected=${option.id === this.value}>
                ${option.label}
              </option>`,
          )}
        </select>
      </label>
    `;
  }
}

defineOnce(FORM_TAGS.select, TwSelect);
