import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { baseStyles, tokenStyles } from '../components/index.ts';
import '../components/index.ts';
import type { CollectionName } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { StoreController } from '../state/index.ts';

/** Gerüst einer Ansicht: zeigt die Anzahl der Objekte ihrer Sammlungen; wird in AP-15 bis AP-17 ausgebaut. */
export class SectionView extends LitElement {
  static sections: readonly CollectionName[] = [];

  static override properties = { language: { type: String } };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: var(--tw-space-m);
      }
    `,
  ];

  declare language: string;

  readonly #store = new StoreController(this);

  constructor() {
    super();
    this.language = '';
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    const sections = (this.constructor as typeof SectionView).sections;
    if (!snapshot) {
      return nothing;
    }
    if (sections.length === 0) {
      return html`<p>${translate('view.soon', this.language)}</p>`;
    }
    return html`
      <div class="grid">
        ${repeat(
          sections,
          (name) => name,
          (name) => html`
            <tw-stat
              label=${translate(`stat.${name}`, this.language)}
              .value=${snapshot[name].length}
            ></tw-stat>
          `,
        )}
      </div>
    `;
  }
}

/** Registriert eine Ansicht, die die Anzahl der genannten Sammlungen zeigt. */
export function defineView(tag: string, sections: readonly CollectionName[]): void {
  customElements.define(
    tag,
    class extends SectionView {
      static override sections = sections;
    },
  );
}
