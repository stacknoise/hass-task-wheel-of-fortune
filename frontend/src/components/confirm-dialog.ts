import { css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, EVENT_CANCEL, EVENT_CONFIRM } from '../constants/index.ts';
import { defineOnce } from './define.ts';
import { ModalElement, modalStyles } from './modal.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/**
 * Modale Rückfrage: Frage mit Bestätigen (`confirm`) und „Abbrechen“. Meldet `tw-confirm` oder
 * `tw-cancel`; das Schließen übernimmt der Aufrufer.
 */
export class TwConfirmDialog extends ModalElement {
  static override properties = {
    ...ModalElement.properties,
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
    modalStyles,
    css`
      .ask {
        max-width: min(28em, calc(100% - 2 * var(--tw-space-m)));
        padding: var(--tw-space-m);
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
      <dialog class="ask" role="alertdialog" aria-label=${this.label} @cancel=${this.onCancel}>
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
          <!-- Der Fokus beginnt beim harmlosen Knopf, damit Enter nicht versehentlich löscht. -->
          <button
            type="button"
            class="action"
            autofocus
            @click=${() => {
              this.#emit(EVENT_CANCEL);
            }}
          >
            ${this.text('form.cancel')}
          </button>
        </div>
      </dialog>
    `;
  }

  #emit(name: string): void {
    this.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true }));
  }
}

defineOnce(COMPONENT_TAGS.confirmDialog, TwConfirmDialog);
