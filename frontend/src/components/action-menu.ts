import { css, html, nothing } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import {
  COMPONENT_TAGS,
  EVENT_ACTION,
  KEY_ARROW_DOWN,
  KEY_ARROW_UP,
  KEY_END,
  KEY_ESCAPE,
  KEY_HOME,
  KEY_TAB,
} from '../constants/index.ts';
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

  override disconnectedCallback(): void {
    document.removeEventListener('click', this.#outside);
    super.disconnectedCallback();
  }

  /** Der Klick-Zuhörer am Dokument hängt nur, solange das Menü offen ist; dann geht der Fokus ins Menü. */
  protected override updated(changed: PropertyValues<this>): void {
    if (changed.has('_open')) {
      if (this._open) {
        document.addEventListener('click', this.#outside);
        this.#items()[0]?.focus();
      } else {
        document.removeEventListener('click', this.#outside);
      }
    }
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
        @keydown=${this.#onKey}
      >
        ${this.label} ▾
      </button>
      ${this._open ? this.#menu() : nothing}
      ${this._pending ? this.#dialog(this._pending) : nothing}
    `;
  }

  #menu(): TemplateResult {
    return html`
      <ul class="menu" role="menu" @keydown=${this.#onKey}>
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

  /** Die bedienbaren Einträge des offenen Menüs. */
  #items(): HTMLButtonElement[] {
    return [...this.renderRoot.querySelectorAll<HTMLButtonElement>('.item:not(:disabled)')];
  }

  /** Escape schließt und gibt den Fokus zurück; Pfeile, Pos1 und Ende wandern durch die Einträge. */
  readonly #onKey = (event: KeyboardEvent): void => {
    if (!this._open) {
      return;
    }
    if (event.key === KEY_ESCAPE) {
      this._open = false;
      this.renderRoot.querySelector<HTMLElement>('.action')?.focus();
    } else if (event.key === KEY_TAB) {
      this._open = false;
    } else {
      this.#move(event);
    }
  };

  #move(event: KeyboardEvent): void {
    const items = this.#items();
    if (items.length === 0) {
      return;
    }
    const current = items.findIndex((item) => item === this.shadowRoot?.activeElement);
    const targets: Readonly<Record<string, number>> = {
      [KEY_ARROW_DOWN]: (current + 1) % items.length,
      [KEY_ARROW_UP]: (current - 1 + items.length) % items.length,
      [KEY_HOME]: 0,
      [KEY_END]: items.length - 1,
    };
    const target = targets[event.key];
    if (target !== undefined) {
      event.preventDefault();
      items[target]?.focus();
    }
  }

  readonly #outside = (event: Event): void => {
    if (this._open && !event.composedPath().includes(this)) {
      this._open = false;
    }
  };
}

defineOnce(COMPONENT_TAGS.actionMenu, TwActionMenu);
