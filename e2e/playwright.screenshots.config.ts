import { defineConfig } from "@playwright/test";

const HA_URL = process.env["HA_URL"] ?? "http://localhost:8123";
const TIMEOUT_MS = 180_000;
const VIEWPORT = { width: 1280, height: 1100 };
const SCALE = 2;

/** Erzeugt die Screenshots der README gegen eine frische Instanz (HA_LANGUAGE=en), siehe docs/screenshots. */
export default defineConfig({
  testDir: "./screenshots",
  globalSetup: "./support/setup.ts",
  timeout: TIMEOUT_MS,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: HA_URL,
    locale: "en-US",
    colorScheme: "light",
    viewport: VIEWPORT,
    deviceScaleFactor: SCALE,
    serviceWorkers: "block",
    launchOptions: { executablePath: process.env["CHROMIUM_PATH"] },
  },
});
