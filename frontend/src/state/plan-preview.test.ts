import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClient } from '../api/index.ts';
import type { PlanPreviewRequest, PlanPreviewWire } from '../api/index.ts';
import { FakeHass } from '../api/fake-hass.testing.ts';
import { PLAN_PREVIEW_DEBOUNCE_MS } from '../constants/index.ts';
import { PlanPreviewLoader } from './plan-preview.ts';

const PLAN: PlanPreviewRequest = {
  interval: { unit: 'day', every: 7 },
  run_days: 30,
  entries: [{ task_id: 't1', mode: 'min_count', min_count: 2 }],
};

const REPLY: PlanPreviewWire = {
  draws_per_run: 4,
  interval_hours: 168,
  persons: {},
  planned: 2,
  capacity: 4,
  empty_draws: 0,
  overloaded_draws: 0,
  peak: 1,
  tracks: [],
  issues: [{ code: 'no_person', blocking: true, params: {} }],
};

let hass: FakeHass;
let client: ApiClient;
let loader: PlanPreviewLoader;
const planCalls = (): number =>
  hass.messages.filter((message) => message.type === 'task_wheel/schedule/plan_preview').length;

beforeEach(() => {
  vi.useFakeTimers();
  hass = new FakeHass();
  hass.replies.set('task_wheel/schedule/plan_preview', REPLY);
  client = new ApiClient(hass);
  loader = new PlanPreviewLoader({ requestUpdate: vi.fn() } as never);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('PlanPreviewLoader', () => {
  it('rechnet erst nach der letzten Eingabe und nur einmal je Planung', async () => {
    loader.request(client, PLAN);
    loader.request(client, { ...PLAN, run_days: 14 });
    loader.request(client, { ...PLAN, run_days: 14 });
    expect(planCalls()).toBe(0);
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    expect(planCalls()).toBe(1);
    expect(hass.messages.at(-1)).toMatchObject({ run_days: 14 });
    expect(loader.value).toEqual(REPLY);
    expect(loader.blocking).toBe(true);
    expect(loader.loading).toBe(false);

    loader.request(client, { ...PLAN, run_days: 14 });
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    expect(planCalls()).toBe(1);
  });

  it('verwirft Anfrage und Bewertung beim Zurücksetzen', async () => {
    loader.request(client, PLAN);
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    loader.request(client, { ...PLAN, run_days: 7 });
    loader.reset();
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    expect(planCalls()).toBe(1);
    expect(loader.value).toBeUndefined();
    expect(loader.blocking).toBe(false);
    loader.request(client, PLAN);
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    expect(planCalls()).toBe(2);
  });

  it('sperrt nichts, wenn die Auswertung fehlschlägt', async () => {
    hass.replies.set('task_wheel/schedule/plan_preview', new Error('offline'));
    loader.request(client, PLAN);
    await vi.advanceTimersByTimeAsync(PLAN_PREVIEW_DEBOUNCE_MS);
    expect(loader.value).toBeUndefined();
    expect(loader.blocking).toBe(false);
  });
});
