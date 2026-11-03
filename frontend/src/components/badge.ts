import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS } from '../constants/index.ts';
import type { Tone } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

/** Kleine Marke mit Text (Status); der Ton bestimmt die Farbe, der Text trägt die Bedeutung. */
export class TwBadge extends LitElement {
  static override properties = { tone: { type: String, reflect: true } };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.85em;
        font-weight: 500;
        color: var(--tw-color-on-primary);
        background: var(--tw-color-neutral);
      }
      :host([tone='success']) {
        background: var(--tw-color-success);
      }
      :host([tone='warning']) {
        background: var(--tw-color-warning);
        color: var(--tw-color-text);
      }
      :host([tone='error']) {
        background: var(--tw-color-error);
      }
      :host([tone='info']) {
        background: var(--tw-color-info);
      }
    `,
  ];

  declare tone: Tone;

  constructor() {
    super();
    this.tone = 'neutral';
  }

  protected override render(): TemplateResult {
    return html`<slot></slot>`;
  }
}

defineOnce(COMPONENT_TAGS.badge, TwBadge);
