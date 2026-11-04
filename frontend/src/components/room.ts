import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

/** Raum einer Aufgabe als kleine Marke; ohne Namen wird nichts gezeigt. */
export class TwRoom extends LitElement {
  static override properties = { name: { type: String } };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: inline-block;
        font-size: 0.85em;
        color: var(--tw-color-text-muted);
      }
      :host([hidden]) {
        display: none;
      }
    `,
  ];

  declare name: string;

  constructor() {
    super();
    this.name = '';
  }

  protected override render(): TemplateResult | typeof nothing {
    return this.name ? html`<span aria-hidden="true">⌂</span> ${this.name}` : nothing;
  }
}

defineOnce(COMPONENT_TAGS.room, TwRoom);
