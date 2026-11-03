import { ContextProvider } from '@lit/context';

import { ApiClient } from '../api/index.ts';
import type { HistoryPage, StatisticsReport, Snapshot } from '../api/index.ts';
import { FakeHass } from '../api/fake-hass.testing.ts';
import {
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SWAP,
  WS_HISTORY_LIST,
  WS_ROUND_DELETE,
  WS_STATISTICS_GET,
} from '../constants/index.ts';
import { Store, storeContext } from '../state/index.ts';

export const SNAPSHOT: Snapshot = {
  persons: [
    { id: 'p1', name: 'Anna', color: '#c05600', load: 'full', jokers_left: 2 },
    { id: 'p2', name: 'Ben', color: '#1a5fd0', load: 'full', jokers_left: 0 },
    { id: 'p3', name: 'Cara', color: '#137333', load: 'paused', jokers_left: 1 },
  ],
  tasks: [
    { id: 't1', name: 'Bad putzen', allowed: ['p1', 'p2', 'p3'], points: 5, swap_allowed: true },
    { id: 't2', name: 'Müll', allowed: ['p1'], points: 2, swap_allowed: false },
  ],
  schedules: [
    {
      id: 's1',
      name: 'Wochenplan',
      task_ids: ['t1', 't2'],
      enabled: true,
      archived: false,
      next_run: '2026-11-09T18:00:00+00:00',
    },
    {
      id: 's2',
      name: 'Monatsplan',
      task_ids: ['t2'],
      enabled: true,
      archived: false,
      next_run: '2026-12-01T09:00:00+00:00',
    },
  ],
  assignments: [
    assignment('a1', 't1', 'p1', 'open'),
    assignment('a2', 't2', 'p1', 'swapped'),
    assignment('a3', 't9', 'p2', 'open', 'r2', 'gone'),
  ],
  rounds: [
    {
      id: 'r1',
      schedule_id: 's1',
      origin: 'manual',
      started_at: '2026-11-02T18:00:00+00:00',
      total: 3,
      closed: 1,
    },
    {
      id: 'r2',
      schedule_id: 'gone',
      origin: 'auto',
      started_at: '2026-11-01T18:00:00+00:00',
      total: 1,
      closed: 0,
    },
  ],
  panel_rounds: [],
  settings: {},
  now: '2026-11-03T12:00:00+00:00',
};

export function assignment(
  id: string,
  taskId: string,
  personId: string,
  status: string,
  roundId = 'r1',
  scheduleId = 's1',
) {
  return {
    id,
    round_id: roundId,
    schedule_id: scheduleId,
    task_id: taskId,
    person_id: personId,
    chance: 0.25,
    points: 5,
    due_at: '2026-11-10T18:00:00+00:00',
    status,
    done_at: status === 'on_time' ? '2026-11-04T10:00:00+00:00' : null,
  };
}

export const HISTORY: HistoryPage = {
  entries: [
    {
      id: 'r1',
      schedule_id: 's1',
      origin: 'manual',
      started_at: '2026-11-02T18:00:00+00:00',
      assignments: [
        assignment('a4', 't1', 'p1', 'on_time'),
        assignment('a5', 't2', 'p9', 'missed'),
      ],
    },
    {
      id: 'r0',
      schedule_id: 'gone',
      origin: 'auto',
      started_at: '2026-10-26T18:00:00+00:00',
      assignments: [assignment('a6', 't7', 'p2', 'late')],
    },
  ],
  next_offset: null,
} as unknown as HistoryPage;

export const REPORT: StatisticsReport = {
  months: ['2026-11'],
  kpis: { assigned: 10, on_time: 5, late: 1, missed: 2, pending: 2, completion_rate: 0.75 },
  standings: [
    { person_id: 'p1', points: 12, fair_points: 8, difference: 4 },
    { person_id: 'p2', points: 4, fair_points: 8, difference: -4 },
    { person_id: 'p9', points: 1, fair_points: 1, difference: 0 },
  ],
  fairness_index: 0.83,
  matrix: { t1: { p1: 3, p2: 1 }, t2: { p1: 2 }, t7: { p2: 1 } },
  weeks: [
    { week_start: '2026-10-12', done: 2, missed: 0, rate: 1 },
    { week_start: '2026-10-19', done: 0, missed: 0, rate: null },
    { week_start: '2026-10-26', done: 1, missed: 1, rate: 0.5 },
    { week_start: '2026-11-02', done: 3, missed: 1, rate: 0.75 },
  ],
  highlights: {
    lucky: 'p2',
    unlucky: 'p1',
    reliable: { person_id: 'p1', on_time_rate: 0.9, closed: 10 },
  },
};

export const EMPTY_REPORT: StatisticsReport = {
  ...REPORT,
  kpis: { assigned: 0, on_time: 0, late: 0, missed: 0, pending: 0, completion_rate: null },
  standings: [],
  weeks: [],
  highlights: { lucky: null, unlucky: null, reliable: null },
};

export function fakeHass(): FakeHass {
  const hass = new FakeHass();
  hass.snapshot = SNAPSHOT;
  hass.replies.set(WS_HISTORY_LIST, HISTORY);
  hass.replies.set(WS_STATISTICS_GET, REPORT);
  hass.replies.set(WS_ASSIGNMENT_COMPLETE, { id: 'a1' });
  hass.replies.set(WS_ASSIGNMENT_SWAP, { id: 'a1' });
  hass.replies.set(WS_ROUND_DELETE, {});

  return hass;
}

/** Hängt eine Ansicht unter einen Elternknoten, der den Store im Kontext bereitstellt. */
export async function mountView<T extends HTMLElement>(
  tag: string,
  hass: FakeHass,
): Promise<T & { updateComplete: Promise<boolean> }> {
  const store = new Store(new ApiClient(hass));
  const host = document.createElement('div');
  new ContextProvider(host, { context: storeContext, initialValue: store });
  const view = document.createElement(tag) as T & {
    language: string;
    updateComplete: Promise<boolean>;
  };
  view.language = 'de';
  host.append(view);
  document.body.append(host);
  await store.start();
  await view.updateComplete;
  return view;
}

export function text(element: Element): string {
  const nodes = [...(element.shadowRoot?.children ?? [])].filter(
    (node) => node.tagName !== 'STYLE',
  );
  return nodes
    .map((node) => node.textContent)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}
