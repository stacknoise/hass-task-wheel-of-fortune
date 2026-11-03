import { css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, EVENT_CANCEL, EVENT_CONFIRM } from '../constants/index.ts';
import { defineOnce } from './define.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/**
 * Modale Rückfrage: Frage mit Bestätigen (`confirm`) und „Abbrechen“. Meldet `tw-confirm` oder
 * `tw-cancel`; das Schließen übernimmt der Aufrufer.
 */
export class TwConfirmDialog extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
    question: { type: String },
    confirm: { type: String },
    primary: { type: Boolean },
    busy: { type: Boolean },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
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
  /** Hebt die Bestätigung als Hauptaktion hervor (statt als Löschen). */
  declare primary: boolean;
  declare busy: boolean;

  constructor() {
    super();
    this.label = '';
    this.question = '';
    this.confirm = '';
    this.primary = false;
    this.busy = false;
  }

  protected override render(): TemplateResult {
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
                this.#emit(EVENT_CONFIRM);
              }}
            >
              ${this.confirm || this.text('form.delete')}
            </button>
            <button
              type="button"
              class="action"
              @click=${() => {
                this.#emit(EVENT_CANCEL);
              }}
            >
              ${this.text('form.cancel')}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  #emit(name: string): void {
    this.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true }));
  }
}

defineOnce(COMPONENT_TAGS.confirmDialog, TwConfirmDialog);
