import { LitElement, css, html } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { COMPONENT_TAGS, EVENT_TAB_SELECT } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';

const HALF = 2;

export interface TabItem {
  readonly id: string;
  readonly label: string;
  readonly href: string;
}

/** Tab-Leiste aus Links; meldet die Wahl als Ereignis und überlässt die Navigation dem Aufrufer. */
export class TwTabBar extends LitElement {
  static override properties = {
    tabs: { attribute: false },
    active: { type: String },
    label: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      nav {
        display: flex;
        gap: var(--tw-space-s);
        overflow-x: auto;
        scrollbar-width: none;
        border-bottom: 1px solid var(--tw-color-divider);
      }
      nav::-webkit-scrollbar {
        display: none;
      }
      a {
        display: flex;
        align-items: center;
        min-height: var(--tw-control-height);
        padding: 0 var(--tw-space-m);
        color: var(--tw-color-text-muted);
        text-decoration: none;
        white-space: nowrap;
        border-bottom: 2px solid transparent;
        transition: color var(--tw-duration);
      }
      a[aria-current='page'] {
        color: var(--tw-color-primary);
        border-bottom-color: var(--tw-color-primary);
      }
    `,
  ];

  declare tabs: readonly TabItem[];
  declare active: string;
  declare label: string;

  constructor() {
    super();
    this.tabs = [];
    this.active = '';
    this.label = '';
  }

  /**
   * Auf schmalen Geräten scrollt die Leiste; der gewählte Tab soll dabei sichtbar bleiben.
   * Nur die Leiste selbst wird verschoben (nicht die Seite) und nur, wenn sich der aktive Tab ändert:
   * `scrollIntoView` würde bei jedem Neuzeichnen die ganze Seite wieder nach oben holen.
   */
  protected override updated(changed: PropertyValues): void {
    if (!changed.has('active') && !changed.has('tabs')) {
      return;
    }
    const nav = this.renderRoot.querySelector('nav');
    const active = this.renderRoot.querySelector<HTMLElement>('a[aria-current="page"]');
    if (nav && active) {
      nav.scrollLeft = active.offsetLeft - (nav.clientWidth - active.offsetWidth) / HALF;
    }
  }

  protected override render(): TemplateResult {
    return html`
      <nav aria-label=${this.label}>
        ${repeat(
          this.tabs,
          (tab) => tab.id,
          (tab) => html`
            <a
              href=${tab.href}
              aria-current=${tab.id === this.active ? 'page' : 'false'}
              @click=${(event: MouseEvent) => {
                this.#select(event, tab);
              }}
              >${tab.label}</a
            >
          `,
        )}
      </nav>
    `;
  }

  #select(event: MouseEvent, tab: TabItem): void {
    event.preventDefault();
    this.dispatchEvent(
      new CustomEvent<string>(EVENT_TAB_SELECT, { detail: tab.id, bubbles: true, composed: true }),
    );
  }
}

defineOnce(COMPONENT_TAGS.tabBar, TwTabBar);
