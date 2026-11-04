import { ContextProvider } from '@lit/context';
import { LitElement, css, html, nothing } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';
import { createRef, ref } from 'lit/directives/ref.js';

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
import type { SectionViewElement } from './views/index.ts';
import { defineOnce } from './components/define.ts';

interface PanelRoute {
  readonly prefix: string;
  readonly path: string;
}

/**
 * Home Assistant ersetzt `hass` bei jeder Zustandsänderung irgendeiner Entität. Das Panel zeichnet
 * nur neu, wenn sich etwas ändert, das es anzeigt: die Sprache, die Räume oder die Dienste.
 */
function hassChanged(next: HassApi | undefined, prev: HassApi | undefined): boolean {
  return (
    next?.language !== prev?.language ||
    next?.locale?.language !== prev?.locale?.language ||
    next?.areas !== prev?.areas ||
    next?.services !== prev?.services ||
    (next === undefined) !== (prev === undefined)
  );
}

/** Einstieg des Panels: Tab-Leiste, Store im Kontext und die nachgeladene Ansicht des gewählten Tabs. */
export class TaskWheelPanel extends LitElement {
  static override properties = {
    hass: { attribute: false, noAccessor: true, hasChanged: hassChanged },
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

  declare route: PanelRoute | undefined;
  declare language: string;
  declare narrow: boolean;
  declare _selected: RouteId;

  readonly #provider = new ContextProvider(this, { context: storeContext });
  readonly #views = new Map<RouteId, SectionViewElement>();
  readonly #loading = new Set<RouteId>();
  /** Ansichten, deren Code sich nicht laden ließ (Netz, Neustart); „Erneut versuchen“ leert die Liste. */
  readonly #failed = new Set<RouteId>();
  readonly #menu = createRef<HTMLElement & { hass?: HassApi }>();
  #hass: HassApi | undefined;
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

  get hass(): HassApi | undefined {
    return this.#hass;
  }

  /** Gibt das neueste `hass` an Client und Menü-Knopf weiter, zeichnet aber nur bei `hassChanged` neu. */
  set hass(value: HassApi | undefined) {
    const previous = this.#hass;
    this.#hass = value;
    if (value) {
      this.#store?.client.useHass(value);
      if (this.#menu.value) {
        this.#menu.value.hass = value;
      }
    }
    this.requestUpdate('hass', previous);
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
            ? html`<ha-menu-button
                ${ref(this.#menu)}
                .hass=${this.hass}
                .narrow=${this.narrow}
              ></ha-menu-button>`
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
    if (!state?.snapshot) {
      return state?.status === 'error'
        ? this.#problem(text('panel.error'), text, () => void this.#store?.reload())
        : html`<p>${text('panel.loading')}</p>`;
    }
    const view = this.#views.get(this.#current());
    const notice =
      state.status === 'error'
        ? this.#problem(text('panel.stale'), text, () => void this.#store?.reload())
        : nothing;
    if (this.#failed.has(this.#current())) {
      return this.#problem(text('panel.view_error'), text, () => {
        this.#failed.clear();
        this.requestUpdate();
      });
    }
    if (!view) {
      return notice;
    }
    view.language = language;
    return html`${notice}${view}`;
  }

  /** Eine Fehlermeldung mit „Erneut versuchen“. */
  #problem(message: string, text: (key: TextKey) => string, retry: () => void): TemplateResult {
    return html`<p role="alert">
      ${message}
      <button type="button" class="action" @click=${retry}>${text('panel.retry')}</button>
    </p>`;
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
    if (this.#views.has(id) || this.#loading.has(id) || this.#failed.has(id)) {
      return;
    }
    this.#loading.add(id);
    try {
      await VIEW_LOADERS[id]();
      this.#views.set(id, document.createElement(VIEW_TAGS[id]) as SectionViewElement);
    } catch {
      this.#failed.add(id);
    } finally {
      this.#loading.delete(id);
      this.requestUpdate();
    }
  }

  #onSelect(event: CustomEvent<RouteId>): void {
    this._selected = event.detail;
    history.pushState(null, '', `${this.route?.prefix ?? ''}${ROUTES[event.detail]}`);
    window.dispatchEvent(new CustomEvent(EVENT_LOCATION_CHANGED));
  }
}

defineOnce(PANEL_ELEMENT_NAME, TaskWheelPanel);
