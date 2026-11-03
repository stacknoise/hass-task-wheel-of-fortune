import { ContextProvider } from '@lit/context';
import { LitElement, css, html, nothing } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';

import { ApiClient } from './api/index.ts';
import type { HassApi } from './api/index.ts';
import { baseStyles, phoneQuery, tokenStyles } from './components/index.ts';
import type { TabItem } from './components/index.ts';
import './components/index.ts';
import {
  DEFAULT_LANGUAGE,
  DEFAULT_ROUTE,
  EVENT_LOCATION_CHANGED,
  EVENT_TAB_SELECT,
  PANEL_ELEMENT_NAME,
  PANEL_HEADING_CLASS,
  ROUTES,
  ROUTE_IDS,
  VIEW_TAGS,
} from './constants/index.ts';
import type { RouteId } from './constants/index.ts';
import { translate } from './i18n/index.ts';
import type { TextKey } from './i18n/index.ts';
import { Store, storeContext } from './state/index.ts';
import { VIEW_LOADERS, routeFromPath } from './views/index.ts';
import type { SectionView } from './views/index.ts';
import { defineOnce } from './components/define.ts';

interface PanelRoute {
  readonly prefix: string;
  readonly path: string;
}

/** Einstieg des Panels: Tab-Leiste, Store im Kontext und die nachgeladene Ansicht des gewählten Tabs. */
export class TaskWheelPanel extends LitElement {
  static override properties = {
    hass: { attribute: false },
    route: { attribute: false },
    language: { type: String },
    narrow: { type: Boolean },
    _selected: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        container-type: inline-size;
        background: var(--tw-color-background);
        min-height: 100%;
      }
      header {
        display: flex;
        align-items: center;
        gap: var(--tw-space-s);
        padding: var(--tw-space-m);
      }
      main {
        padding: var(--tw-space-m);
        padding-bottom: calc(var(--tw-space-m) + env(safe-area-inset-bottom, 0px));
      }
      h1 {
        margin: 0;
        font-weight: 400;
      }
      @container ${phoneQuery} {
        header {
          padding: var(--tw-space-s) var(--tw-space-m);
        }
        h1 {
          font-size: 1.4em;
        }
        main {
          padding: var(--tw-space-s);
          padding-bottom: calc(var(--tw-space-s) + env(safe-area-inset-bottom, 0px));
        }
      }
    `,
  ];

  declare hass: HassApi | undefined;
  declare route: PanelRoute | undefined;
  declare language: string;
  declare narrow: boolean;
  declare _selected: RouteId;

  readonly #provider = new ContextProvider(this, { context: storeContext });
  readonly #views = new Map<RouteId, SectionView>();
  readonly #loading = new Set<RouteId>();
  #store: Store | undefined;
  #unlisten: (() => void) | undefined;

  constructor() {
    super();
    this.language = '';
    this.narrow = false;
    this._selected = DEFAULT_ROUTE;
    this.addEventListener(EVENT_TAB_SELECT, (event) => {
      this.#onSelect(event as CustomEvent<RouteId>);
    });
  }

  override connectedCallback(): void {
    super.connectedCallback();
    if (this.hass) {
      this.#startStore(this.hass);
    }
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.#unlisten?.();
    this.#store?.stop();
    this.#store = undefined;
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('hass') && this.hass) {
      this.#startStore(this.hass);
    }
    void this.#ensureView(this.#current());
  }

  protected override render(): TemplateResult {
    const language = this.#language();
    const text = (key: TextKey): string => translate(key, language);
    return html`
      <header>
        ${
          this.narrow
            ? html`<ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>`
            : nothing
        }
        <h1 class=${PANEL_HEADING_CLASS}>${text('panel.title')}</h1>
      </header>
      <tw-tab-bar
        .tabs=${this.#tabs(text)}
        .active=${this.#current()}
        .label=${text('panel.nav')}
      ></tw-tab-bar>
      <main>${this.#body(language, text)}</main>
    `;
  }

  #body(language: string, text: (key: TextKey) => string): TemplateResult | typeof nothing {
    const state = this.#store?.state;
    if (state?.status === 'error') {
      return html`<p>${text('panel.error')}</p>`;
    }
    if (!state?.snapshot) {
      return html`<p>${text('panel.loading')}</p>`;
    }
    const view = this.#views.get(this.#current());
    if (!view) {
      return nothing;
    }
    view.language = language;
    return html`${view}`;
  }

  #language(): string {
    return (
      this.language || (this.hass?.locale?.language ?? this.hass?.language ?? DEFAULT_LANGUAGE)
    );
  }

  #current(): RouteId {
    return routeFromPath(this.route?.path) ?? this._selected;
  }

  #tabs(text: (key: TextKey) => string): readonly TabItem[] {
    const prefix = this.route?.prefix ?? '';
    return ROUTE_IDS.map((id) => ({
      id,
      label: text(`tab.${id}`),
      href: `${prefix}${ROUTES[id]}`,
    }));
  }

  #startStore(hass: HassApi): void {
    if (this.#store) {
      return;
    }
    const store = new Store(new ApiClient(hass));
    this.#store = store;
    this.#provider.setValue(store);
    this.#unlisten = store.listen(() => {
      this.requestUpdate();
    });
    void store.start();
  }

  async #ensureView(id: RouteId): Promise<void> {
    if (this.#views.has(id) || this.#loading.has(id)) {
      return;
    }
    this.#loading.add(id);
    await VIEW_LOADERS[id]();
    this.#loading.delete(id);
    const view = document.createElement(VIEW_TAGS[id]) as SectionView;
    this.#views.set(id, view);
    this.requestUpdate();
  }

  #onSelect(event: CustomEvent<RouteId>): void {
    this._selected = event.detail;
    history.pushState(null, '', `${this.route?.prefix ?? ''}${ROUTES[event.detail]}`);
    window.dispatchEvent(new CustomEvent(EVENT_LOCATION_CHANGED));
  }
}

defineOnce(PANEL_ELEMENT_NAME, TaskWheelPanel);
