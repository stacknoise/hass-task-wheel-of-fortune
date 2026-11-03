import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_TAGS } from '../constants/index.ts';
import { emitChange } from './change.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

const STEP = 1;
const DECREASE = '−';
const INCREASE = '+';

/** Zahl mit Minus- und Plus-Knopf; hält den Wert zwischen `min` und `max`. */
export class TwStepper extends LitElement {
  static override properties = {
    label: { type: String },
    value: { type: Number },
    min: { type: Number },
    max: { type: Number },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .row {
        display: inline-flex;
        align-items: center;
        gap: var(--tw-space-s);
      }
      button {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 1px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      button:disabled {
        opacity: 0.4;
        cursor: default;
      }
      output {
        min-width: 3ch;
        text-align: center;
        font-weight: 500;
      }
    `,
  ];

  declare label: string;
  declare value: number;
  declare min: number;
  declare max: number;

  constructor() {
    super();
    this.label = '';
    this.value = 0;
    this.min = 0;
    this.max = Number.MAX_SAFE_INTEGER;
  }

  protected override render(): TemplateResult {
    return html`
      <span class="label">${this.label}</span>
      <div class="row" role="group" aria-label=${this.label}>
        <button
          type="button"
          ?disabled=${this.value <= this.min}
          aria-label=${DECREASE}
          @click=${() => {
            this.#move(-STEP);
          }}
        >
          ${DECREASE}
        </button>
        <output>${this.value}</output>
        <button
          type="button"
          ?disabled=${this.value >= this.max}
          aria-label=${INCREASE}
          @click=${() => {
            this.#move(STEP);
          }}
        >
          ${INCREASE}
        </button>
      </div>
    `;
  }

  #move(delta: number): void {
    emitChange(this, Math.min(this.max, Math.max(this.min, this.value + delta)));
  }
}

defineOnce(FORM_TAGS.stepper, TwStepper);
