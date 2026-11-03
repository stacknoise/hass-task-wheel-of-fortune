import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { COMPONENT_TAGS, EVENT_CHIP_SELECT } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';

export interface ChipItem {
  readonly id: string;
  readonly label: string;
  /** Farbpunkt vor der Beschriftung (z. B. Farbe einer Person). */
  readonly color?: string;
}

/** Auswahl aus Chips (genau einer ist gewählt); meldet die Wahl als Ereignis. */
export class TwChips extends LitElement {
  static override properties = {
    items: { attribute: false },
    selected: { type: String },
    label: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      div {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      button {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        min-height: 36px;
        padding: 0 14px;
        border: 1px solid var(--tw-color-divider);
        border-radius: 18px;
        background: var(--tw-color-surface);
        color: var(--tw-color-text);
        font: inherit;
        cursor: pointer;
      }
      button[aria-pressed='true'] {
        background: var(--tw-color-primary);
        border-color: var(--tw-color-primary);
        color: var(--tw-color-on-primary);
      }
      .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: var(--dot);
      }
    `,
  ];

  declare items: readonly ChipItem[];
  declare selected: string;
  declare label: string;

  constructor() {
    super();
    this.items = [];
    this.selected = '';
    this.label = '';
  }

  protected override render(): TemplateResult {
    return html`
      <div role="group" aria-label=${this.label}>
        ${repeat(
          this.items,
          (item) => item.id,
          (item) => html`
            <button
              type="button"
              aria-pressed=${item.id === this.selected ? 'true' : 'false'}
              @click=${() => {
                this.#select(item.id);
              }}
            >
              ${item.color ? html`<span class="dot" style="--dot: ${item.color}"></span>` : ''}
              ${item.label}
            </button>
          `,
        )}
      </div>
    `;
  }

  #select(id: string): void {
    this.dispatchEvent(
      new CustomEvent<string>(EVENT_CHIP_SELECT, { detail: id, bubbles: true, composed: true }),
    );
  }
}

customElements.define(COMPONENT_TAGS.chips, TwChips);
