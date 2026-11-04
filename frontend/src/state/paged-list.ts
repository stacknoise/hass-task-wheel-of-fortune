import type { ReactiveControllerHost } from 'lit';

import type { ApiClient } from '../api/index.ts';
import { AsyncValue } from './async-value.ts';
import type { AsyncStatus } from './async-value.ts';
import type { StoreController } from './context.ts';
import { LiveLoad } from './revision.ts';

/** Eine Seite einer Liste mit dem Beginn der nächsten (leer auf der letzten Seite). */
export interface Page<T> {
  readonly entries: readonly T[];
  readonly next_offset: number | null;
}

type Fetch<T> = (client: ApiClient, offset: number, limit: number) => Promise<Page<T>>;

interface Loaded<T> {
  readonly items: readonly T[];
  readonly next: number | null;
}

/**
 * Seitenweise geladene Liste einer Ansicht (Historie, Entscheidungslog): erste Seite, „Weitere laden“
 * und Neuladen nach jeder Änderung der Zuteilungen, ohne dass schon geladene Seiten verloren gehen.
 */
export class PagedList<T> {
  readonly #data: AsyncValue<Loaded<T>>;
  readonly #live = new LiveLoad();
  readonly #store: StoreController;
  readonly #fetch: Fetch<T>;
  readonly #pageSize: number;
  readonly #maxSize: number;

  constructor(
    host: ReactiveControllerHost,
    store: StoreController,
    fetch: Fetch<T>,
    pageSize: number,
    maxSize: number,
  ) {
    this.#data = new AsyncValue<Loaded<T>>(host);
    this.#store = store;
    this.#fetch = fetch;
    this.#pageSize = pageSize;
    this.#maxSize = maxSize;
  }

  get status(): AsyncStatus {
    return this.#data.status;
  }

  /** Bisher geladene Einträge; vor der ersten Antwort `undefined`. */
  get items(): readonly T[] | undefined {
    return this.#data.value?.items;
  }

  get hasMore(): boolean {
    return (this.#data.value?.next ?? null) !== null;
  }

  /** Aus `willUpdate` der Ansicht: lädt beim ersten Mal und nach jeder Änderung der Zuteilungen. */
  sync(): void {
    if (this.#live.due(this.#store.state?.snapshot, this.#store.client !== undefined)) {
      this.#run(this.#data.value ? 'keep' : 'first');
    }
  }

  /** Lädt ab der ersten Seite neu (nach einer Änderung des Filters). */
  reload(): void {
    this.#run('first');
  }

  /** Hängt die nächste Seite an. */
  more(): void {
    this.#run('more');
  }

  /** Holt alle bisher gezeigten Einträge neu (nach einer Änderung im Hintergrund). */
  refresh(): void {
    this.#run('keep');
  }

  #run(mode: 'first' | 'more' | 'keep'): void {
    const client = this.#store.client;
    if (!client) {
      return;
    }
    const before = mode === 'more' ? this.#data.value : undefined;
    const shown = mode === 'keep' ? (this.#data.value?.items.length ?? 0) : 0;
    const limit = Math.min(Math.max(this.#pageSize, shown), this.#maxSize);
    void this.#data.run(async () => {
      const page = await this.#fetch(client, before?.next ?? 0, limit);
      return { items: [...(before?.items ?? []), ...page.entries], next: page.next_offset };
    });
  }
}
