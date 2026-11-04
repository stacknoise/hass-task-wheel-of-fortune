import { ContextConsumer, createContext } from '@lit/context';
import type { ReactiveController, ReactiveControllerHost } from 'lit';

import type { ApiClient, AreaOption } from '../api/index.ts';
import { areaNames } from './areas.ts';
import type { AreaNames } from './areas.ts';
import type { Store, StoreState } from './store.ts';

export const storeContext = createContext<Store>(Symbol('task-wheel-store'));

const NO_AREAS: readonly AreaOption[] = [];

type Host = ReactiveControllerHost & HTMLElement;

/** Liest den Store aus dem Kontext und lässt den Host bei jeder Änderung neu rendern. */
export class StoreController implements ReactiveController {
  readonly #host: Host;
  #store: Store | undefined;
  #unlisten: (() => void) | undefined;

  constructor(host: Host) {
    this.#host = host;
    host.addController(this);
    new ContextConsumer(host, {
      context: storeContext,
      subscribe: true,
      callback: (store) => {
        this.#attach(store);
      },
    });
  }

  /** Der aktuelle Stand; vor dem Eintreffen des Stores leer. */
  get state(): StoreState | undefined {
    return this.#store?.state;
  }

  /** Der API-Zugang des Stores; vor dem Eintreffen des Stores leer. */
  get client(): ApiClient | undefined {
    return this.#store?.client;
  }

  /** Die Räume von Home Assistant als Nachschlagetabelle (zwischengespeichert, solange sie sich nicht ändern). */
  areaNames(): AreaNames {
    return areaNames(this.client?.areas() ?? NO_AREAS);
  }

  hostDisconnected(): void {
    this.#unlisten?.();
    this.#unlisten = undefined;
    this.#store = undefined;
  }

  #attach(store: Store): void {
    this.#unlisten?.();
    this.#store = store;
    this.#unlisten = store.listen(() => {
      this.#host.requestUpdate();
    });
    this.#host.requestUpdate();
  }
}
