import { defineConfig } from '@playwright/test';

const HA_URL = process.env['HA_URL'] ?? 'http://localhost:8123';
const TIMEOUT_MS = 60_000;

export default defineConfig({
  testDir: './tests',
  globalSetup: './support/setup.ts',
  timeout: TIMEOUT_MS,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: HA_URL,
    locale: 'de-DE',
    // Der Service-Worker der Oberfläche lädt die Seite neu, sobald er die Kontrolle übernimmt (mitten im Test)
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
  },
});
