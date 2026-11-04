import { describe, expect, it, vi } from 'vitest';

import { ApiClient } from '../api/index.ts';
import { EMPTY_SNAPSHOT, FakeHass } from '../api/fake-hass.testing.ts';
import { Store } from './store.ts';

function create(): { hass: FakeHass; store: Store } {
  const hass = new FakeHass();
  return { hass, store: new Store(new ApiClient(hass)) };
}

/** Ein API-Zugang, dessen Abonnements von Hand erfüllt werden. */
function manualClient(): {
  client: ApiClient;
  resolveSubscribe: (index: number) => void;
  unsubscribed: number[];
  reconnect: () => void;
} {
  const resolvers: (() => void)[] = [];
  const unsubscribed: number[] = [];
  let reconnect = (): void => undefined;
  const client = {
    language: () => 'de',
    onReconnect: (listener: () => void) => {
      reconnect = listener;
      return () => undefined;
    },
    subscribe: () => {
      const index = resolvers.length;
      return new Promise<() => void>((resolve) => {
        resolvers.push(() => {
          resolve(() => unsubscribed.push(index));
        });
      });
    },
    snapshot: () => Promise.resolve(EMPTY_SNAPSHOT),
  } as unknown as ApiClient;
  return {
    client,
    resolveSubscribe: (index) => resolvers[index]?.(),
    unsubscribed,
    reconnect: () => {
      reconnect();
    },
  };
}

describe('Store', () => {
  it('beendet ein Abonnement, das erst nach stop() eintrifft', async () => {
    const manual = manualClient();
    const store = new Store(manual.client);
    const started = store.start();
    store.stop();
    manual.resolveSubscribe(0);
    await started;
    expect(manual.unsubscribed).toEqual([0]);
    expect(store.state.status).toBe('loading');
  });

  it('behält nach einem Reconnect während des Ladens nur das neueste Abonnement', async () => {
    const manual = manualClient();
    const store = new Store(manual.client);
    const first = store.start();
    manual.reconnect();
    manual.resolveSubscribe(0);
    manual.resolveSubscribe(1);
    await first;
    await vi.waitFor(() => {
      expect(store.state.status).toBe('ready');
    });
    expect(manual.unsubscribed).toEqual([0]);
  });

  it('abonniert zuerst und lädt dann den Snapshot', async () => {
    const { hass, store } = create();
    await store.start();
    expect(hass.calls).toEqual(['task_wheel/subscribe', 'task_wheel/snapshot']);
    expect(store.state.status).toBe('ready');
    expect(store.state.snapshot?.persons).toHaveLength(2);
  });

  it('wendet Deltas nach dem Snapshot an und meldet es den Zuhörern', async () => {
    const { hass, store } = create();
    const listener = vi.fn();
    store.listen(listener);
    await store.start();
    listener.mockClear();
    hass.emit({ persons: { upsert: [{ id: 'p3', name: 'Zed' }], remove: ['p1'] } });
    expect(store.state.snapshot?.persons.map((item) => item.id)).toEqual(['p2', 'p3']);
    expect(listener).toHaveBeenCalledOnce();
  });

  it('verwirft Deltas vor dem Snapshot und nach dem Beenden', async () => {
    const { hass, store } = create();
    hass.emit({ persons: { upsert: [], remove: [] } });
    await store.start();
    store.stop();
    hass.emit({ persons: { upsert: [{ id: 'x' }], remove: [] } });
    expect(store.state.snapshot?.persons).toHaveLength(2);
    expect(hass.unsubscribed).toBe(1);
    expect(hass.listenerCount).toBe(0);
  });

  it('meldet Fehler und erholt sich nach dem Wiederaufbau der Verbindung', async () => {
    const { hass, store } = create();
    hass.failSnapshot = true;
    await store.start();
    expect(store.state.status).toBe('error');
    hass.failSnapshot = false;
    hass.reconnect();
    await vi.waitFor(() => {
      expect(store.state.status).toBe('ready');
    });
    expect(hass.unsubscribed).toBe(1);
  });

  it('Zuhörer lassen sich abmelden', async () => {
    const { store } = create();
    const listener = vi.fn();
    store.listen(listener)();
    await store.start();
    expect(listener).not.toHaveBeenCalled();
  });
});
