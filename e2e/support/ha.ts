/** Einrichtung einer frisch gestarteten Home-Assistant-Instanz über deren HTTP-Schnittstellen. */

import { writeFileSync } from 'node:fs';

export const AUTH_FILE = new URL('../.auth.json', import.meta.url);
export const DOMAIN = 'task_wheel';
const USER = { name: 'Test', username: 'test', password: 'e2e-passwort-2026', language: 'de' };

export interface Tokens {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly token_type: string;
  readonly expires_in: number;
}

async function send<T>(
  base: string,
  path: string,
  init: { body?: unknown; token?: string; form?: URLSearchParams },
): Promise<T> {
  const headers: Record<string, string> = {};
  if (init.token) {
    headers['Authorization'] = `Bearer ${init.token}`;
  }
  if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(`${base}${path}`, {
    method: 'POST',
    headers,
    body: init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body)),
  });
  if (!response.ok) {
    throw new Error(`${path}: ${String(response.status)} ${await response.text()}`);
  }
  return (await response.json()) as T;
}

/** Legt den Benutzer an (Onboarding) und liefert die Zugangsdaten. */
async function onboard(base: string): Promise<Tokens> {
  const clientId = `${base}/`;
  const { auth_code: code } = await send<{ auth_code: string }>(base, '/api/onboarding/users', {
    body: { client_id: clientId, ...USER },
  });
  const tokens = await send<Tokens>(base, '/auth/token', {
    form: new URLSearchParams({ grant_type: 'authorization_code', code, client_id: clientId }),
  });
  for (const step of ['core_config', 'analytics']) {
    await send(base, `/api/onboarding/${step}`, { body: {}, token: tokens.access_token });
  }
  await send(base, '/api/onboarding/integration', {
    body: { client_id: clientId, redirect_uri: clientId },
    token: tokens.access_token,
  });
  return tokens;
}

/** Richtet die Integration über ihren Config Flow ein (ein Bestätigungsschritt). */
async function addIntegration(base: string, token: string): Promise<void> {
  const flow = await send<{ flow_id: string }>(base, '/api/config/config_entries/flow', {
    body: { handler: DOMAIN },
    token,
  });
  await send(base, `/api/config/config_entries/flow/${flow.flow_id}`, { body: {}, token });
}

/** Richtet eine frische Instanz ein und merkt sich die Zugangsdaten für die Tests. */
export async function prepare(base: string): Promise<void> {
  const tokens = await onboard(base);
  await addIntegration(base, tokens.access_token);
  writeFileSync(AUTH_FILE, JSON.stringify(tokens));
}
