import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { COMPONENT_TAGS, EVENT_ACTION } from '../constants/index.ts';
import './confirm-dialog.ts';
import { defineOnce } from './define.ts';
import { LocalizedElement } from './localized.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';

/** Ein Eintrag des Aktionsmenüs; mit `question` fragt das Menü vor dem Auslösen nach. */
export interface ActionItem {
  readonly id: string;
  readonly label: string;
  readonly title?: string;
  readonly disabled?: boolean;
  readonly question?: string;
  /** Hebt die Rückfrage-Bestätigung als Hauptaktion hervor (statt als Löschen). */
  readonly primary?: boolean;
}

/** Ein Knopf „Aktionen“ mit Menü; meldet `tw-action` mit der Kennung des gewählten Eintrags. */
export class TwActionMenu extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    label: { type: String },
    items: { attribute: false },
    busy: { type: Boolean },
    _open: { state: true },
    _pending: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      :host {
        position: relative;
        display: inline-block;
      }
      .menu {
        position: absolute;
        top: 100%;
        right: 0;
        z-index: 5;
        min-width: 100%;
        margin: var(--tw-space-s) 0 0;
        padding: var(--tw-space-s) 0;
        list-style: none;
        border: 1px solid var(--tw-color-divider);
        border-radius: var(--tw-radius);
        background: var(--tw-color-surface);
      }
      .menu li {
        padding: 0;
        border: 0;
      }
      .item {
        width: 100%;
        padding: var(--tw-space-s) var(--tw-space-m);
        border: 0;
        background: none;
        color: var(--tw-color-text);
        font: inherit;
        text-align: left;
        white-space: nowrap;
        cursor: pointer;
      }
      .item:disabled {
        color: var(--tw-color-text-muted);
        cursor: not-allowed;
      }
    `,
  ];

  declare label: string;
  declare items: readonly ActionItem[];
  declare busy: boolean;
  declare _open: boolean;
  declare _pending: ActionItem | undefined;

  constructor() {
    super();
    this.label = '';
    this.items = [];
    this.busy = false;
    this._open = false;
    this._pending = undefined;
  }

  override connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener('click', this.#outside);
  }

  override disconnectedCallback(): void {
    document.removeEventListener('click', this.#outside);
    super.disconnectedCallback();
  }

  protected override render(): TemplateResult {
    return html`
      <button
        type="button"
        class="action"
        aria-haspopup="menu"
        aria-expanded=${this._open ? 'true' : 'false'}
        ?disabled=${this.busy}
        @click=${() => {
          this._open = !this._open;
        }}
        @keydown=${this.#escape}
      >
        ${this.label} ▾
      </button>
      ${this._open ? this.#menu() : nothing}
      ${this._pending ? this.#dialog(this._pending) : nothing}
    `;
  }

  #menu(): TemplateResult {
    return html`
      <ul class="menu" role="menu" @keydown=${this.#escape}>
        ${repeat(
          this.items,
          (item) => item.id,
          (item) => html`
            <li role="none">
              <button
                type="button"
                role="menuitem"
                class="item"
                title=${item.title ?? ''}
                ?disabled=${item.disabled === true}
                @click=${() => {
                  this.#choose(item);
                }}
              >
                ${item.label}
              </button>
            </li>
          `,
        )}
      </ul>
    `;
  }

  #dialog(item: ActionItem): TemplateResult {
    return html`<tw-confirm-dialog
      language=${this.language}
      label=${item.label}
      confirm=${item.label}
      question=${item.question ?? ''}
      ?primary=${item.primary === true}
      ?busy=${this.busy}
      @tw-confirm=${(event: Event) => {
        event.stopPropagation();
        this._pending = undefined;
        this.#emit(item.id);
      }}
      @tw-cancel=${(event: Event) => {
        event.stopPropagation();
        this._pending = undefined;
      }}
    ></tw-confirm-dialog>`;
  }

  #choose(item: ActionItem): void {
    this._open = false;
    if (item.question) {
      this._pending = item;
    } else {
      this.#emit(item.id);
    }
  }

  #emit(id: string): void {
    this.dispatchEvent(
      new CustomEvent(EVENT_ACTION, { detail: id, bubbles: true, composed: true }),
    );
  }

  readonly #escape = (event: KeyboardEvent): void => {
    if (event.key === 'Escape') {
      this._open = false;
    }
  };

  readonly #outside = (event: Event): void => {
    if (this._open && !event.composedPath().includes(this)) {
      this._open = false;
    }
  };
}

defineOnce(COMPONENT_TAGS.actionMenu, TwActionMenu);
