import { readFileSync } from 'node:fs';
import type { Page } from '@playwright/test';

import { AUTH_FILE, type Tokens } from './ha.ts';

const ONE_DAY_MS = 86_400_000;

/** Meldet den Browser mit den Zugangsdaten aus der Einrichtung an (vor dem Laden der Seite). */
export async function signIn(page: Page, base: string): Promise<void> {
  const tokens = JSON.parse(readFileSync(AUTH_FILE, 'utf8')) as Tokens;
  const stored = {
    ...tokens,
    hassUrl: base,
    clientId: `${base}/`,
    expires: Date.now() + ONE_DAY_MS,
  };
  await page.addInitScript((value) => {
    localStorage.setItem('hassTokens', JSON.stringify(value));
  }, stored);
}

/** Schickt einen Befehl der WebSocket-API über die Verbindung der geöffneten Oberfläche. */
export async function callWS<T>(page: Page, message: Record<string, unknown>): Promise<T> {
  return page.evaluate(async (payload) => {
    const root = document.querySelector('home-assistant') as unknown as {
      hass: { callWS: (message: unknown) => Promise<unknown> };
    };
    return root.hass.callWS(payload);
  }, message) as Promise<T>;
}
