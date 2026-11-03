import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, INITIAL_LENGTH } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/** Runde Marke einer Person: Anfangsbuchstabe auf ihrer Farbe. */
export class TwAvatar extends LitElement {
  static override properties = { name: { type: String }, color: { type: String } };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: var(--avatar, var(--tw-color-neutral));
        color: var(--tw-color-on-primary);
        font-size: 0.8em;
        font-weight: 700;
        flex: none;
      }
    `,
  ];

  declare name: string;
  declare color: string;

  constructor() {
    super();
    this.name = '';
    this.color = '';
  }

  protected override willUpdate(): void {
    this.style.setProperty('--avatar', this.color || null);
  }

  protected override render(): TemplateResult {
    return html`${this.name.slice(0, INITIAL_LENGTH).toUpperCase()}`;
  }
}

customElements.define(COMPONENT_TAGS.avatar, TwAvatar);
