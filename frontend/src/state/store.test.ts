import { describe, expect, it, vi } from 'vitest';

import { ApiClient } from '../api/index.ts';
import { FakeHass } from '../api/fake-hass.testing.ts';
import { Store } from './store.ts';

function create(): { hass: FakeHass; store: Store } {
  const hass = new FakeHass();
  return { hass, store: new Store(new ApiClient(hass)) };
}

describe('Store', () => {
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
    hass.emit({ persons: { upsert: [{ id: 'p3' }], remove: ['p1'] } });
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
