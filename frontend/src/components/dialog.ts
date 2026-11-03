import { css, html, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';

import {
  COMPONENT_TAGS,
  DIALOG_COMPACT_MAX_WIDTH,
  DIALOG_MAX_WIDTH_EM,
  EVENT_CANCEL,
  KEY_ESCAPE,
} from '../constants/index.ts';
import { defineOnce } from './define.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles } from './styles.ts';

/**
 * Modales Fenster für Formulare: Titel mit Schließen-Knopf, Inhalt im Standard-Slot (scrollt),
 * feste Fußzeile im Slot `actions`. Auf dem Smartphone füllt es das Fenster aus. Meldet `tw-cancel`
 * bei Escape und beim Schließen-Knopf; das Schließen übernimmt der Aufrufer.
 */
export class TwDialog extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 9;
        display: grid;
        place-items: center;
        background: rgb(0 0 0 / 50%);
      }
      .dialog {
        display: flex;
        flex-direction: column;
        box-sizing: border-box;
        width: min(${unsafeCSS(DIALOG_MAX_WIDTH_EM)}em, 100%);
        max-height: 90dvh;
        border: 1px solid var(--tw-color-divider);
        border-radius: var(--tw-radius);
        background: var(--tw-color-surface);
        color: var(--tw-color-text);
        outline: none;
      }
      header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--tw-space-s);
        padding: var(--tw-space-s) var(--tw-space-m);
        border-bottom: 1px solid var(--tw-color-divider);
      }
      h2 {
        margin: 0;
        font-size: 1.2em;
        font-weight: 500;
      }
      .close {
        min-width: 44px;
        min-height: 44px;
        border: 0;
        background: none;
        color: inherit;
        font: inherit;
        font-size: 1.4em;
        cursor: pointer;
      }
      .close:focus-visible {
        outline: 2px solid var(--tw-color-primary);
      }
      .body {
        flex: 1 1 auto;
        overflow-y: auto;
        overscroll-behavior: contain;
        padding: var(--tw-space-m);
      }
      footer {
        padding: var(--tw-space-s) var(--tw-space-m);
        border-top: 1px solid var(--tw-color-divider);
      }
      @media (max-width: ${unsafeCSS(DIALOG_COMPACT_MAX_WIDTH)}px) {
        .dialog {
          width: 100%;
          height: 100dvh;
          max-height: none;
          border: 0;
          border-radius: 0;
        }
      }
    `,
  ];

  declare label: string;

  constructor() {
    super();
    this.label = '';
  }

  protected override firstUpdated(): void {
    this.renderRoot.querySelector<HTMLElement>('.dialog')?.focus();
  }

  protected override render(): TemplateResult {
    return html`
      <div class="backdrop">
        <div
          class="dialog"
          role="dialog"
          aria-modal="true"
          aria-label=${this.label}
          tabindex="-1"
          @keydown=${this.#onKey}
        >
          <header>
            <h2>${this.label}</h2>
            <button
              type="button"
              class="close"
              aria-label=${this.text('form.cancel')}
              @click=${this.#cancel}
            >
              ✕
            </button>
          </header>
          <div class="body"><slot></slot></div>
          <footer><slot name="actions"></slot></footer>
        </div>
      </div>
    `;
  }

  readonly #onKey = (event: KeyboardEvent): void => {
    if (event.key === KEY_ESCAPE) {
      event.stopPropagation();
      this.#cancel();
    }
  };

  readonly #cancel = (): void => {
    this.dispatchEvent(new CustomEvent(EVENT_CANCEL, { bubbles: true, composed: true }));
  };
}

defineOnce(COMPONENT_TAGS.dialog, TwDialog);
