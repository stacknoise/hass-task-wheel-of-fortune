import { css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, EVENT_CONFIRM } from '../constants/index.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/**
 * Löschen mit Rückfrage: erst der Knopf, dann die Frage mit „Löschen“ und „Abbrechen“.
 * Erst die Bestätigung löst `tw-confirm` aus; die Frage ist die Warnung der Aufrufer (`question`).
 */
export class TwConfirmDelete extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
    question: { type: String },
    busy: { type: Boolean },
    _asking: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      :host {
        display: block;
      }
      .ask {
        margin-top: var(--tw-space-s);
        padding: var(--tw-space-s);
        border: 1px solid var(--tw-color-error);
        border-radius: var(--tw-radius);
      }
      .danger {
        background: var(--tw-color-error);
        border-color: var(--tw-color-error);
        color: var(--tw-color-on-primary);
      }
    `,
  ];

  declare label: string;
  declare question: string;
  declare busy: boolean;
  declare _asking: boolean;

  constructor() {
    super();
    this.label = '';
    this.question = '';
    this.busy = false;
    this._asking = false;
  }

  protected override render(): TemplateResult {
    return this._asking
      ? html`
          <div class="ask" role="alertdialog" aria-label=${this.label}>
            <p>${this.question}</p>
            <div class="row">
              <button
                type="button"
                class="action danger"
                ?disabled=${this.busy}
                @click=${() => {
                  this._asking = false;
                  this.dispatchEvent(
                    new CustomEvent(EVENT_CONFIRM, { bubbles: true, composed: true }),
                  );
                }}
              >
                ${this.text('form.delete')}
              </button>
              <button
                type="button"
                class="action"
                @click=${() => {
                  this._asking = false;
                }}
              >
                ${this.text('form.cancel')}
              </button>
            </div>
          </div>
        `
      : html`<button
          type="button"
          class="action"
          ?disabled=${this.busy}
          @click=${() => {
            this._asking = true;
          }}
        >
          ${this.label}
        </button>`;
  }
}

customElements.define(COMPONENT_TAGS.confirmDelete, TwConfirmDelete);
