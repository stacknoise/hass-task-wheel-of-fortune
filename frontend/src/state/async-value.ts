import type { ReactiveControllerHost } from 'lit';

export type AsyncStatus = 'idle' | 'loading' | 'ready' | 'error';

/**
 * Ein asynchron geladener Wert für eine Ansicht. Ein neuer Aufruf macht einen noch laufenden
 * ungültig; der alte Wert bleibt bis zur Antwort stehen.
 */
export class AsyncValue<T> {
  readonly #host: ReactiveControllerHost;
  #run = 0;
  status: AsyncStatus = 'idle';
  value: T | undefined;

  constructor(host: ReactiveControllerHost) {
    this.#host = host;
  }

  async run(task: () => Promise<T>): Promise<void> {
    this.#run += 1;
    const ticket = this.#run;
    this.#set('loading');
    try {
      const value = await task();
      if (ticket === this.#run) {
        this.value = value;
        this.#set('ready');
      }
    } catch {
      if (ticket === this.#run) {
        this.#set('error');
      }
    }
  }

  #set(status: AsyncStatus): void {
    this.status = status;
    this.#host.requestUpdate();
  }
}
