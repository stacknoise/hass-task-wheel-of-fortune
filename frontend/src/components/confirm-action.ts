import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, EVENT_CONFIRM } from '../constants/index.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/**
 * Aktion mit Rückfrage (Löschen, „Bleibt unerledigt“): erst der Knopf (`label`), dann die Frage mit
 * Bestätigen (`confirm`, sonst „Löschen“) und „Abbrechen“. Erst die Bestätigung löst `tw-confirm` aus.
 */
export class TwConfirmAction extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
    question: { type: String },
    confirm: { type: String },
    blocked: { type: String },
    busy: { type: Boolean },
    primary: { type: Boolean },
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
      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 10;
        display: grid;
        place-items: center;
        padding: var(--tw-space-m);
        background: rgb(0 0 0 / 50%);
      }
      .ask {
        max-width: 28em;
        padding: var(--tw-space-m);
        border: 1px solid var(--tw-color-divider);
        border-radius: var(--tw-radius);
        background: var(--tw-color-surface);
        color: var(--tw-color-text);
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
  /** Beschriftung der Bestätigung; leer heißt „Löschen“. */
  declare confirm: string;
  /** Grund, warum Löschen gesperrt ist; leer, wenn es erlaubt ist. */
  declare blocked: string;
  declare busy: boolean;
  /** Hebt Knopf und Bestätigung als Hauptaktion hervor (statt als Löschen). */
  declare primary: boolean;
  declare _asking: boolean;

  constructor() {
    super();
    this.label = '';
    this.question = '';
    this.confirm = '';
    this.blocked = '';
    this.busy = false;
    this.primary = false;
    this._asking = false;
  }

  protected override render(): TemplateResult {
    return html`
      <button
        type="button"
        class="action ${this.primary ? 'primary' : ''}"
        title=${this.blocked}
        ?disabled=${this.busy || this.blocked !== ''}
        @click=${() => {
          this._asking = true;
        }}
      >
        ${this.label}
      </button>
      ${this._asking ? this.#dialog() : nothing}
    `;
  }

  #dialog(): TemplateResult {
    return html`
      <div class="backdrop">
        <div class="ask" role="alertdialog" aria-modal="true" aria-label=${this.label}>
          <p>${this.question}</p>
          <div class="row">
            <button
              type="button"
              class="action ${this.primary ? 'primary' : 'danger'}"
              ?disabled=${this.busy}
              @click=${() => {
                this._asking = false;
                this.dispatchEvent(
                  new CustomEvent(EVENT_CONFIRM, { bubbles: true, composed: true }),
                );
              }}
            >
              ${this.confirm || this.text('form.delete')}
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
      </div>
    `;
  }
}

customElements.define(COMPONENT_TAGS.confirmAction, TwConfirmAction);
