import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Kennzahl mit Beschriftung. Kennt nur ihre Eigenschaften. */
export class TwStat extends LitElement {
  static override properties = {
    label: { type: String },
    value: { type: Number },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        background: var(--tw-color-surface);
        border: 1px solid var(--tw-color-divider);
        border-radius: var(--tw-radius);
        padding: var(--tw-space-m);
      }
      .value {
        font-size: 2em;
        font-weight: 500;
      }
      .label {
        color: var(--tw-color-text-muted);
      }
    `,
  ];

  declare label: string;
  declare value: number;

  constructor() {
    super();
    this.label = '';
    this.value = 0;
  }

  protected override render(): TemplateResult {
    return html`
      <div class="value">${this.value}</div>
      <div class="label">${this.label}</div>
    `;
  }
}

customElements.define(COMPONENT_TAGS.stat, TwStat);
