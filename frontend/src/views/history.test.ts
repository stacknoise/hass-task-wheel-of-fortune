import { describe, expect, it, vi } from 'vitest';

import { VIEW_TAGS, WS_HISTORY_LIST, WS_ROUND_DELETE } from '../constants/index.ts';
import { press } from '../components/press.testing.ts';
import { HISTORY, SNAPSHOT, fakeHass, mountView, text } from './fixtures.testing.ts';
import { VIEW_LOADERS } from './registry.ts';

const download = vi.hoisted(() => vi.fn());
vi.mock('./download.ts', () => ({ downloadText: download }));

async function mount(hass = fakeHass()) {
  await VIEW_LOADERS.history();
  const view = await mountView(VIEW_TAGS.history, hass);
  await vi.waitFor(() => {
    expect(text(view)).toContain('Wochenplan');
  });
  return { view, hass };
}

function button(view: Element, label: string): HTMLButtonElement | undefined {
  return [...(view.shadowRoot?.querySelectorAll('button') ?? [])].find((b) =>
    b.textContent.includes(label),
  );
}

describe('Historie', () => {
  it('zeigt die Runden zugeklappt mit Zusammenfassung', async () => {
    const { view } = await mount();
    const content = text(view);
    expect(content).toContain('Manuell');
    expect(content).toContain('Automatisch');
    expect(content).toContain('1 von 2 erledigt');
    expect(content).toContain('Gelöschter Zeitplan');
    expect(view.shadowRoot?.querySelector('table')).toBeNull();
  });

  it('klappt eine Runde mit Zuteilungen auf und wieder zu', async () => {
    const { view } = await mount();
    button(view, 'Wochenplan')?.click();
    await view.updateComplete;
    const content = text(view);
    expect(content).toContain('Bad putzen');
    expect(content).toContain('Unbekannte Person');
    expect(content).toContain('Verpasst');
    expect(content).toContain('25 %');
    button(view, 'Wochenplan')?.click();
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('table')).toBeNull();
  });

  it('filtert serverseitig nach Person', async () => {
    const { view, hass } = await mount();
    const chips = view.shadowRoot?.querySelector('tw-chips');
    [...(chips?.shadowRoot?.querySelectorAll('button') ?? [])]
      .find((b) => b.textContent.includes('Anna'))
      ?.click();
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({
        type: WS_HISTORY_LIST,
        person_id: 'p1',
        offset: 0,
      });
    });
  });

  it('lädt weitere Seiten nach', async () => {
    const hass = fakeHass();
    hass.replies.set(WS_HISTORY_LIST, { ...HISTORY, next_offset: 2 });
    const { view } = await mount(hass);
    button(view, 'Weitere laden')?.click();
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({ offset: 2 });
    });
  });

  it('holt bei einer Änderung im Hintergrund alle bisher gezeigten Runden neu', async () => {
    const hass = fakeHass();
    const [first] = HISTORY.entries;
    const entries = Array.from({ length: 25 }, (_, index) => ({
      ...(first as NonNullable<typeof first>),
      id: `r${String(index)}`,
    }));
    hass.replies.set(WS_HISTORY_LIST, { entries, next_offset: 25 });
    await mount(hass);
    hass.emit({
      assignments: {
        upsert: [{ ...SNAPSHOT.assignments[0], id: 'a1', status: 'done' }],
        remove: [],
      },
    });
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({ offset: 0, limit: 25 });
    });
  });

  it('exportiert alle Seiten als CSV', async () => {
    const hass = fakeHass();
    hass.callWS = ((message: { type: string; offset?: number }) => {
      hass.messages.push(message);
      if (message.type !== WS_HISTORY_LIST) {
        return Promise.resolve(hass.snapshot);
      }
      return Promise.resolve(message.offset ? HISTORY : { ...HISTORY, next_offset: 2 });
    }) as typeof hass.callWS;
    const { view } = await mount(hass);
    button(view, 'CSV exportieren')?.click();
    await vi.waitFor(() => {
      expect(download).toHaveBeenCalledOnce();
    });
    const [name, content] = download.mock.calls[0] as [string, string];
    expect(name).toBe('task-wheel-history.csv');
    expect(content.split('\r\n')).toHaveLength(1 + 3 + 3);
    expect(content).toContain('"Bad putzen"');
  });

  it('lädt neu, wenn sich Zuteilungen live ändern (neue Auslosung, Statuswechsel)', async () => {
    const { hass } = await mount();
    const loads = () => hass.calls.filter((call) => call === WS_HISTORY_LIST).length;
    expect(loads()).toBe(1);
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

  it('meldet einen fehlgeschlagenen Export', async () => {
    const { view, hass } = await mount();
    hass.callWS = () => Promise.reject(new Error('x'));
    button(view, 'CSV exportieren')?.click();
    await vi.waitFor(() => {
      expect(text(view)).toContain('Der Export ist fehlgeschlagen.');
    });
  });

  it('zeigt leeren Zustand und Ladefehler', async () => {
    const empty = fakeHass();
    empty.replies.set(WS_HISTORY_LIST, { entries: [], next_offset: null });
    await VIEW_LOADERS.history();
    const view = await mountView(VIEW_TAGS.history, empty);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Noch keine Runden.');
    });
    const failing = fakeHass();
    failing.callWS = ((message: { type: string }) =>
      message.type === WS_HISTORY_LIST
        ? Promise.reject(new Error('x'))
        : Promise.resolve(failing.snapshot)) as typeof failing.callWS;
    const broken = await mountView(VIEW_TAGS.history, failing);
    await vi.waitFor(() => {
      expect(text(broken)).toContain('konnten nicht geladen werden');
    });
  });

  it('löscht eine Runde nach der Rückfrage und lädt die Liste neu', async () => {
    const { view, hass } = await mount();
    const remove = view.shadowRoot?.querySelectorAll('tw-confirm-action')[1] as HTMLElement & {
      updateComplete: Promise<boolean>;
    };
    await press(remove, 'Auslosung löschen');
    expect(
      remove.shadowRoot?.querySelector('tw-confirm-dialog')?.shadowRoot?.textContent,
    ).toContain('1 Zuteilungen');
    await press(remove, 'Löschen');
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ROUND_DELETE)).toEqual({
        type: WS_ROUND_DELETE,
        round_id: 'r0',
      });
    });
    await vi.waitFor(() => {
      expect(hass.calls.filter((call) => call === WS_HISTORY_LIST)).toHaveLength(2);
    });
  });

  it('meldet einen Fehler beim Löschen', async () => {
    const { view, hass } = await mount();
    hass.callWS = () => Promise.reject(new Error('nein'));
    const remove = view.shadowRoot?.querySelectorAll('tw-confirm-action')[1] as HTMLElement & {
      updateComplete: Promise<boolean>;
    };
    await press(remove, 'Auslosung löschen');
    await press(remove, 'Löschen');
    await vi.waitFor(() => {
      expect(text(view)).toContain('Die Aktion ist fehlgeschlagen.');
    });
  });
});
