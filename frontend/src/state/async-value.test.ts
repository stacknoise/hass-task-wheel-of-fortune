import { describe, expect, it } from 'vitest';

import { AsyncValue } from './async-value.ts';

function host(): { requestUpdate: () => void; updates: number } {
  const state = { updates: 0, requestUpdate: () => (state.updates += 1) };
  return state;
}

describe('AsyncValue', () => {
  it('liefert den Wert und meldet jede Änderung', async () => {
    const owner = host();
    const value = new AsyncValue<number>(owner as never);
    await value.run(() => Promise.resolve(1));
    expect([value.status, value.value, owner.updates]).toEqual(['ready', 1, 2]);
  });

  it('meldet einen Fehler und behält den alten Wert', async () => {
    const value = new AsyncValue<number>(host() as never);
    await value.run(() => Promise.resolve(1));
    await value.run(() => Promise.reject(new Error('x')));
    expect([value.status, value.value]).toEqual(['error', 1]);
  });

  it('verwirft die Antwort eines überholten Aufrufs', async () => {
    const value = new AsyncValue<string>(host() as never);
    let release: (text: string) => void = () => undefined;
    const slow = value.run(() => new Promise<string>((resolve) => (release = resolve)));
    await value.run(() => Promise.resolve('neu'));
    release('alt');
    await slow;
    expect(value.value).toBe('neu');
  });

  it('verwirft auch den Fehler eines überholten Aufrufs', async () => {
    const value = new AsyncValue<string>(host() as never);
    let fail: (error: Error) => void = () => undefined;
    const slow = value.run(() => new Promise<string>((_, reject) => (fail = reject)));
    await value.run(() => Promise.resolve('neu'));
    fail(new Error('spät'));
    await slow;
    expect(value.status).toBe('ready');
  });
});
