import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';
import { initialOf } from './format.ts';

/**
 * Runde Marke einer Person: Anfangsbuchstabe auf ihrer Farbe. Größe, Schrift und Rand lassen sich
 * über `--tw-avatar-size`, `--tw-avatar-font` und `--tw-avatar-border` anpassen.
 */
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
        box-sizing: border-box;
        width: var(--tw-avatar-size, 28px);
        aspect-ratio: 1;
        border: var(--tw-avatar-border, none);
        border-radius: 50%;
        background: var(--avatar, var(--tw-color-neutral));
        color: var(--tw-color-on-primary);
        font-size: var(--tw-avatar-font, 0.8em);
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
    return html`${initialOf(this.name)}`;
  }
}

defineOnce(COMPONENT_TAGS.avatar, TwAvatar);
