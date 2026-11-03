import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { FORM_TAGS } from '../constants/index.ts';
import { emitChange } from './change.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

export interface ChipOption {
  readonly id: string;
  readonly label: string;
  /** Optionale Farbe als Punkt vor dem Text (Farbe einer Person). */
  readonly color?: string;
}

/** Mehrfachauswahl aus Chips; meldet die gewählten Kennungen in der Reihenfolge der Optionen. */
export class TwChipSelect extends LitElement {
  static override properties = {
    label: { type: String },
    options: { attribute: false },
    selected: { attribute: false },
    error: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      button {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 36px;
        padding: 0 14px;
        border-radius: 18px;
        border: 1px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      button[aria-pressed='true'] {
        border-color: var(--tw-color-primary);
        background: color-mix(in srgb, var(--tw-color-primary) 15%, transparent);
      }
      .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
      }
    `,
  ];

  declare label: string;
  declare options: readonly ChipOption[];
  declare selected: readonly string[];
  declare error: string;

  constructor() {
    super();
    this.label = '';
    this.options = [];
    this.selected = [];
    this.error = '';
  }

  protected override render(): TemplateResult {
    return html`
      <span class="label">${this.label}</span>
      <div class="chips" role="group" aria-label=${this.label}>
        ${repeat(
          this.options,
          (option) => option.id,
          (option) => html`
            <button
              type="button"
              aria-pressed=${this.selected.includes(option.id) ? 'true' : 'false'}
              @click=${() => {
                this.#toggle(option.id);
              }}
            >
              ${
                option.color
                  ? html`<span class="dot" style="background:${option.color}"></span>`
                  : nothing
              }
              ${option.label}
            </button>
          `,
        )}
      </div>
      ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : nothing}
    `;
  }

  #toggle(id: string): void {
    const next = new Set(this.selected);
    if (!next.delete(id)) {
      next.add(id);
    }
    emitChange(
      this,
      this.options.map((option) => option.id).filter((optionId) => next.has(optionId)),
    );
  }
}

defineOnce(FORM_TAGS.chipSelect, TwChipSelect);
