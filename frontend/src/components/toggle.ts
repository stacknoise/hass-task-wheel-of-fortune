import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { FORM_TAGS } from '../constants/index.ts';
import { emitChange } from './change.ts';
import { formStyles } from './formStyles.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Schalter mit Beschriftung (Kontrollkästchen mit Schalter-Rolle). */
export class TwToggle extends LitElement {
  static override properties = { label: { type: String }, checked: { type: Boolean } };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      label {
        display: flex;
        align-items: center;
        gap: var(--tw-space-s);
        min-height: 40px;
        cursor: pointer;
      }
      input {
        width: 20px;
        height: 20px;
      }
    `,
  ];

  declare label: string;
  declare checked: boolean;

  constructor() {
    super();
    this.label = '';
    this.checked = false;
  }

  protected override render(): TemplateResult {
    return html`
      <label>
        <input
          type="checkbox"
          role="switch"
          .checked=${this.checked}
          @change=${(event: Event) => {
            emitChange(this, (event.target as HTMLInputElement).checked);
          }}
        />
        <span>${this.label}</span>
      </label>
    `;
  }
}

customElements.define(FORM_TAGS.toggle, TwToggle);
