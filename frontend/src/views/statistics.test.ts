import { describe, expect, it, vi } from 'vitest';

import { VIEW_TAGS, WS_STATISTICS_GET } from '../constants/index.ts';
import { EMPTY_REPORT, SNAPSHOT, fakeHass, mountView, text } from './fixtures.testing.ts';
import { VIEW_LOADERS } from './registry.ts';

async function mount(hass = fakeHass()) {
  await VIEW_LOADERS.statistics();
  const view = await mountView(VIEW_TAGS.statistics, hass);
  return { view, hass };
}

describe('Statistik', () => {
  it('zeigt Kennzahlen, Balken, Wochenquote, Matrix und Auszeichnungen', async () => {
    const { view } = await mount();
    await vi.waitFor(() => {
      expect(text(view)).toContain('Fairness-Index');
    });
    const content = text(view);
    expect(content).toContain('75 %');
    expect(content).toContain('5 pünktlich, 1 verspätet');
    expect(content).toContain('2 noch offen');
    expect(content).toContain('0,83');
    expect(content).toContain('Gelöschte Aufgabe');
    expect(content).toContain('Glückspilz');
    expect(content).toContain('4 unter dem fairen Anteil');
    expect(content).toContain('90 % pünktlich bei 10 abgeschlossenen Zuteilungen');
    const root = view.shadowRoot;
    expect(root?.querySelectorAll('.bar-row')).toHaveLength(2);
    expect(root?.querySelectorAll('polyline')).toHaveLength(2);
    expect(root?.querySelectorAll('circle')).toHaveLength(3);
    expect(root?.querySelector('svg')?.getAttribute('aria-label')?.replace(/\s/g, ' ')).toContain(
      'zuletzt 75 %',
    );
  });

  it('zeigt je Aufgabe Soll und tatsächlich Verlostes je Fenster in einer eigenen Box', async () => {
    const { view } = await mount();
    await vi.waitFor(() => {
      expect(text(view)).toContain('Verlosungen je Aufgabe');
    });
    const cells = [...(view.shadowRoot?.querySelectorAll('td.goal-cell') ?? [])];
    expect(cells.map((cell) => cell.querySelector('strong')?.textContent.trim())).toEqual([
      '2 / 3',
      '3 / 3',
      '1 / 3',
    ]);
    expect(cells.map((cell) => cell.getAttribute('data-state'))).toEqual(['under', 'met', 'under']);
    expect(text(view)).toContain('max. 3× in 2 Monaten');
    const first = view.shadowRoot?.querySelector('tr:has(td.goal-cell) td');
    expect(first?.textContent).toContain('Bad putzen');
    const room = first?.querySelector('tw-room') as (HTMLElement & { name: string }) | null;
    expect(room?.name).toBe('Unbekannter Raum');
  });

  it('zeigt in der Matrix leer, wo eine Person die Aufgabe nicht darf', async () => {
    const { view } = await mount();
    await vi.waitFor(() => {
      expect(view.shadowRoot?.querySelector('td.cell')).not.toBeNull();
    });
    const rows = [...(view.shadowRoot?.querySelectorAll('tbody tr') ?? [])];
    const muell = rows.find((row) => row.textContent.includes('Müll'));
    const cells = [...(muell?.querySelectorAll('td.cell') ?? [])].map((c) => c.textContent.trim());
    expect(cells).toEqual(['2', '–', '–']);
  });

  it('lädt neu, wenn sich Zuteilungen live ändern (neue Auslosung, Statuswechsel)', async () => {
    const { hass } = await mount();
    const loads = () => hass.calls.filter((call) => call === WS_STATISTICS_GET).length;
    await vi.waitFor(() => {
      expect(loads()).toBe(1);
    });
    hass.emit({
      assignments: {
        upsert: [{ ...SNAPSHOT.assignments[0], id: 'a1', status: 'done' }],
        remove: [],
      },
    });
    await vi.waitFor(() => {
      expect(loads()).toBe(2);
    });
    hass.emit({ persons: { upsert: [], remove: [] } });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(loads()).toBe(2);
  });

  it('lädt beim Wechsel des Zeitraums neu', async () => {
    const { view, hass } = await mount();
    await vi.waitFor(() => {
      expect(hass.calls).toContain(WS_STATISTICS_GET);
    });
    const chips = view.shadowRoot?.querySelector('tw-chips');
    [...(chips?.shadowRoot?.querySelectorAll('button') ?? [])]
      .find((b) => b.textContent.includes('12 Monate'))
      ?.click();
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({ type: WS_STATISTICS_GET, months: 12, weeks: 8 });
    });
  });

  it('zeigt leeren Zustand und Ladefehler', async () => {
    const empty = fakeHass();
    empty.replies.set(WS_STATISTICS_GET, EMPTY_REPORT);
    const { view } = await mount(empty);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Noch keine Zuteilungen im Zeitraum.');
    });
    const failing = fakeHass();
    failing.callWS = ((message: { type: string }) =>
      message.type === WS_STATISTICS_GET
        ? Promise.reject(new Error('x'))
        : Promise.resolve(failing.snapshot)) as typeof failing.callWS;
    const broken = await mountView(VIEW_TAGS.statistics, failing);
    await vi.waitFor(() => {
      expect(text(broken)).toContain('konnten nicht geladen werden');
    });
  });

  it('kommt ohne Auszeichnungen und ohne Quote aus', async () => {
    const hass = fakeHass();
    hass.replies.set(WS_STATISTICS_GET, {
      ...EMPTY_REPORT,
      kpis: { ...EMPTY_REPORT.kpis, assigned: 1, pending: 1 },
      weeks: [{ week_start: '2026-11-02', done: 0, missed: 0, rate: null }],
    });
    const { view } = await mount(hass);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Noch nicht genug Daten.');
    });
    expect(view.shadowRoot?.querySelectorAll('polyline')).toHaveLength(0);
  });
});
