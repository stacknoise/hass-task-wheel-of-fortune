import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { FORM_TAGS, KEY_ARROW_LEFT, KEY_ARROW_RIGHT } from '../constants/index.ts';
import { emitChange } from './change.ts';
import { defineOnce } from './define.ts';
import { baseStyles, tokenStyles } from './styles.ts';

export interface SectionTab {
  readonly id: string;
  readonly label: string;
  /** Zähler hinter dem Namen (Anzahl der Aufgaben, der Hinweise); 0 und fehlend zeigen nichts. */
  readonly badge?: number;
  /** Hebt den Zähler als Warnung hervor. */
  readonly warn?: boolean;
}

/** Reiterleiste innerhalb eines Dialogs; meldet die Kennung des gewählten Reiters als `tw-change`. */
export class TwSectionTabs extends LitElement {
  static override properties = {
    tabs: { attribute: false },
    active: { type: String },
    label: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      .tabs {
        display: flex;
        overflow-x: auto;
        scrollbar-width: none;
        border-bottom: 1px solid var(--tw-color-divider);
      }
      .tabs::-webkit-scrollbar {
        display: none;
      }
      button {
        flex: 1 1 auto;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--tw-space-s);
        min-height: var(--tw-control-height);
        padding: 0 var(--tw-space-m);
        border: 0;
        border-bottom: 2px solid transparent;
        background: none;
        color: var(--tw-color-text-muted);
        font: inherit;
        white-space: nowrap;
        cursor: pointer;
      }
      button[aria-selected='true'] {
        color: var(--tw-color-primary);
        border-bottom-color: var(--tw-color-primary);
        font-weight: 500;
      }
      button:focus-visible {
        outline: 2px solid var(--tw-color-primary);
        outline-offset: -2px;
      }
      .badge {
        padding: 0 var(--tw-space-s);
        border-radius: 1em;
        background: var(--tw-color-fill);
        color: var(--tw-color-text-muted);
        font-size: 0.8em;
        font-weight: 400;
      }
      .badge.warn {
        background: color-mix(in srgb, var(--tw-color-warning) 25%, transparent);
        color: var(--tw-color-text);
      }
    `,
  ];

  declare tabs: readonly SectionTab[];
  declare active: string;
  declare label: string;

  constructor() {
    super();
    this.tabs = [];
    this.active = '';
    this.label = '';
  }

  protected override render(): TemplateResult {
    return html`
      <div class="tabs" role="tablist" aria-label=${this.label} @keydown=${this.#arrow}>
        ${repeat(
          this.tabs,
          (tab) => tab.id,
          (tab) => html`
            <button
              type="button"
              role="tab"
              id=${tab.id}
              aria-selected=${tab.id === this.active ? 'true' : 'false'}
              tabindex=${tab.id === this.active ? 0 : -1}
              @click=${() => {
                emitChange(this, tab.id);
              }}
            >
              ${tab.label}
              ${
                tab.badge
                  ? html`<span class=${tab.warn ? 'badge warn' : 'badge'}>${tab.badge}</span>`
                  : nothing
              }
            </button>
          `,
        )}
      </div>
    `;
  }

  /** Pfeiltasten wählen den Nachbarn und setzen den Fokus dorthin. */
  readonly #arrow = (event: KeyboardEvent): void => {
    const step = event.key === KEY_ARROW_RIGHT ? 1 : event.key === KEY_ARROW_LEFT ? -1 : 0;
    if (step === 0) {
      return;
    }
    const index = this.tabs.findIndex((tab) => tab.id === this.active);
    const next = this.tabs[index + step];
    if (next) {
      event.preventDefault();
      emitChange(this, next.id);
      this.renderRoot.querySelector<HTMLElement>(`#${next.id}`)?.focus();
    }
  };
}

defineOnce(FORM_TAGS.sectionTabs, TwSectionTabs);
