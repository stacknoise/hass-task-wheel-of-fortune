import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS } from '../constants/index.ts';
import './confirm-dialog.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/**
 * Aktion mit Rückfrage (Löschen, „Bleibt unerledigt“): erst der Knopf (`label`), dann der Dialog
 * (`tw-confirm-dialog`). Erst die Bestätigung löst `tw-confirm` aus.
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

  static override styles = [tokenStyles, baseStyles, viewStyles];

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
      ${
        this._asking
          ? html`<tw-confirm-dialog
              language=${this.language}
              label=${this.label}
              question=${this.question}
              confirm=${this.confirm}
              ?primary=${this.primary}
              ?busy=${this.busy}
              @tw-confirm=${this.#close}
              @tw-cancel=${this.#close}
            ></tw-confirm-dialog>`
          : nothing
      }
    `;
  }

  readonly #close = (): void => {
    this._asking = false;
  };
}

customElements.define(COMPONENT_TAGS.confirmAction, TwConfirmAction);
