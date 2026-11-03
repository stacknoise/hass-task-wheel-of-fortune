import { LitElement, html } from 'lit';
import type { TemplateResult } from 'lit';

import { PANEL_ELEMENT_NAME, PANEL_HEADING_CLASS } from './constants/index.ts';
import { translate } from './i18n/index.ts';

/** Einstieg des Panels (Gerüst). Rendert ausschließlich Lit-Templates. */
export class TaskWheelPanel extends LitElement {
  static override properties = { language: { type: String } };

  declare language: string;

  constructor() {
    super();
    this.language = '';
  }

  protected override render(): TemplateResult {
    return html`
      <h1 class=${PANEL_HEADING_CLASS}>${translate('panel.title', this.language)}</h1>
      <p>${translate('panel.placeholder', this.language)}</p>
    `;
  }
}

customElements.define(PANEL_ELEMENT_NAME, TaskWheelPanel);
