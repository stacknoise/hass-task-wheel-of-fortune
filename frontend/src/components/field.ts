import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_TAGS } from '../constants/index.ts';
import { emitChange } from './change.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

/** Beschriftetes Eingabefeld (Text, Zeit, Datum, Datum mit Uhrzeit); meldet den Text bei jeder Eingabe. */
export class TwField extends LitElement {
  static override properties = {
    label: { type: String },
    value: { type: String },
    type: { type: String },
    error: { type: String },
    placeholder: { type: String },
    maxlength: { type: Number },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      input {
        width: 100%;
      }
      input[aria-invalid='true'] {
        border-color: var(--tw-color-error);
      }
    `,
  ];

  declare label: string;
  declare value: string;
  declare type: string;
  declare error: string;
  declare placeholder: string;
  declare maxlength: number;

  constructor() {
    super();
    this.label = '';
    this.value = '';
    this.type = 'text';
    this.error = '';
    this.placeholder = '';
    this.maxlength = 0;
  }

  protected override render(): TemplateResult {
    return html`
      <label>
        <span class="label">${this.label}</span>
        <input
          class="control"
          .value=${this.value}
          type=${this.type}
          placeholder=${this.placeholder}
          maxlength=${this.maxlength > 0 ? this.maxlength : nothing}
          aria-invalid=${this.error ? 'true' : 'false'}
          @input=${(event: Event) => {
            emitChange(this, (event.target as HTMLInputElement).value);
          }}
        />
      </label>
      ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : nothing}
    `;
  }
}

defineOnce(FORM_TAGS.field, TwField);
