import { describe, expect, it, vi } from 'vitest';

import {
  VIEW_TAGS,
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SKIP,
  WS_ASSIGNMENT_SWAP,
  WS_HISTORY_LIST,
  WS_ROUND_DELETE,
  WS_STATISTICS_GET,
} from '../constants/index.ts';
import { press } from '../components/press.testing.ts';
import { fakeHass, mountView, text } from './fixtures.testing.ts';
import { VIEW_LOADERS } from './registry.ts';

async function mount(hass = fakeHass()) {
  await VIEW_LOADERS.overview();
  const view = await mountView(VIEW_TAGS.overview, hass);
  await vi.waitFor(() => {
    expect(hass.calls).toContain(WS_STATISTICS_GET);
  });
  await view.updateComplete;
  return { view, hass };
}

function buttons(view: Element, label: string): HTMLButtonElement[] {
  return [...(view.shadowRoot?.querySelectorAll('button') ?? [])].filter((button) =>
    button.textContent.includes(label),
  );
}

/** Öffnet das Aktionsmenü der `index`-ten Zuteilung. */
async function openMenu(view: HTMLElement, index = 0): Promise<HTMLElement> {
  const menu = view.shadowRoot?.querySelectorAll<HTMLElement>('tw-action-menu')[
    index
  ] as HTMLElement;
  menu.shadowRoot?.querySelector('button')?.click();
  await (menu as HTMLElement & { updateComplete: Promise<boolean> }).updateComplete;
  return menu;
}

/** Wählt einen Menüeintrag; mit `confirm` auch die Bestätigung im Dialog. */
async function choose(view: HTMLElement, label: string, confirm = false, index = 0): Promise<void> {
  const menu = await openMenu(view, index);
  await press(menu, label);
  if (confirm) {
    await press(menu, label);
  }
}

describe('Übersicht', () => {
  it('zeigt die nächste Auslosung, Zuteilungen je Zeitplan, Punkte und Aktivität', async () => {
    const { view } = await mount();
    await vi.waitFor(() => {
      expect(text(view)).toContain('Aktivität');
      expect(text(view)).toContain('Bad putzen');
    });
    const content = text(view);
    expect(content).toContain('Wochenplan');
    expect(content).toContain('2 Aufgaben');
    expect(content).toContain('Zeitplan 1 von 2');
    expect(content).toContain('Ohne Zeitplan');
    expect(content).toContain('Gelöschte Aufgabe');
    expect(content).toContain('4 offen');
    expect(content).toContain('Getauscht');
    expect(content).toContain('fair: 8');
  });

  it('blättert durch die Zeitpläne', async () => {
    const { view } = await mount();
    buttons(view, '›')[0]?.click();
    await view.updateComplete;
    expect(text(view)).toContain('Monatsplan');
    buttons(view, '‹')[0]?.click();
    await view.updateComplete;
    expect(text(view)).toContain('Zeitplan 1 von 2');
  });

  it('filtert nach Person', async () => {
    const { view } = await mount();
    const chips = view.shadowRoot?.querySelector('tw-chips');
    const ben = [...(chips?.shadowRoot?.querySelectorAll('button') ?? [])].find((button) =>
      button.textContent.includes('Ben'),
    );
    ben?.click();
    await view.updateComplete;
    const shown = view.shadowRoot?.querySelector('.assignments')?.textContent ?? '';
    expect(shown).toContain('Küche');
    expect(shown).toContain('Gelöschte Aufgabe');
    expect(shown).not.toContain('Bad putzen');
  });

  it('erledigt eine Zuteilung und lädt Punkte und Aktivität neu', async () => {
    const { view, hass } = await mount();
    await choose(view, 'Erledigt', true);
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ASSIGNMENT_COMPLETE)).toEqual({
        type: WS_ASSIGNMENT_COMPLETE,
        assignment_id: 'a1',
      });
    });
    // Die Statistik lädt erst nach dem Delta des Servers neu, und zwar nur einmal.
    expect(hass.calls.filter((call) => call === WS_STATISTICS_GET)).toHaveLength(1);
    hass.emit({ assignments: { upsert: [], remove: ['a1'] } });
    await vi.waitFor(() => {
      expect(hass.calls.filter((call) => call === WS_STATISTICS_GET)).toHaveLength(2);
    });
  });

  it('lädt Punkte und Aktivität neu, wenn sich Zuteilungen live ändern', async () => {
    const { hass } = await mount();
    const loads = () => hass.calls.filter((call) => call === WS_STATISTICS_GET).length;
    expect(loads()).toBe(1);
    hass.emit({ assignments: { upsert: [], remove: ['a1'] } });
    await vi.waitFor(() => {
      expect(loads()).toBe(2);
    });
  });

  it('bietet Personen der Auslosung mit ihrer offenen Aufgabe zum Tausch an', async () => {
    const { view, hass } = await mount();
    await choose(view, 'Tauschen');
    await view.updateComplete;
    const choice = view.shadowRoot?.querySelector('.swap');
    expect(choice?.textContent).toContain('Ben (Küche)');
    expect(choice?.textContent).not.toContain('Cara');
    expect(choice?.textContent).not.toContain('Anna');
    const ben = [...(choice?.querySelectorAll('button') ?? [])].find((b) =>
      b.textContent.includes('Ben'),
    );
    ben?.click();
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ASSIGNMENT_SWAP)).toMatchObject({
        assignment_id: 'a1',
        to_person_id: 'p2',
      });
    });
  });

  it('markiert eine Zuteilung erst nach der Rückfrage als „Bleibt unerledigt“', async () => {
    const { view, hass } = await mount();
    const menu = await openMenu(view);
    await press(menu, 'Bleibt unerledigt');
    expect(menu.shadowRoot?.querySelector('tw-confirm-dialog')?.shadowRoot?.textContent).toContain(
      'zählt in der Statistik wie verpasst',
    );
    expect(hass.messages.some((m) => m.type === WS_ASSIGNMENT_SKIP)).toBe(false);
    await press(menu, 'Bleibt unerledigt');
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ASSIGNMENT_SKIP)).toEqual({
        type: WS_ASSIGNMENT_SKIP,
        assignment_id: 'a1',
      });
    });
  });

  it('sperrt das Tauschen, wenn die Aufgabe es nicht erlaubt oder die Zuteilung schon getauscht ist', async () => {
    const { view } = await mount();
    const swap: HTMLButtonElement[] = [];
    for (const index of [0, 1, 3]) {
      const menu = await openMenu(view, index);
      const item = [...(menu.shadowRoot?.querySelectorAll('button') ?? [])].find((button) =>
        button.textContent.includes('Tauschen'),
      );
      swap.push(item as HTMLButtonElement);
    }
    expect(swap[0]?.disabled).toBe(false);
    expect(swap[0]?.title).toBe('');
    expect(swap[1]?.disabled).toBe(true);
    expect(swap[1]?.title).toBe('Diese Zuteilung wurde schon getauscht.');
    expect(swap[2]?.disabled).toBe(true);
    expect(swap[2]?.title).toBe('Diese Aufgabe darf nicht getauscht werden.');
  });

  it('weist ohne Gegenstück darauf hin', async () => {
    const { view, hass } = await mount();
    hass.emit({ assignments: { upsert: [], remove: ['a7'] } });
    await view.updateComplete;
    await choose(view, 'Tauschen');
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('.swap')?.textContent).toContain(
      'Niemand aus dieser Auslosung hat eine offene Aufgabe',
    );
  });

  it('klappt die Tauschauswahl wieder zu', async () => {
    const { view } = await mount();
    await choose(view, 'Tauschen');
    await view.updateComplete;
    buttons(view, 'Abbrechen')[0]?.click();
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('.swap')).toBeNull();
  });

  it('zeigt einen Fehler, wenn die Aktion scheitert', async () => {
    const { view, hass } = await mount();
    hass.callWS = () => Promise.reject(new Error('nein'));
    await choose(view, 'Erledigt', true);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Die Aktion ist fehlgeschlagen.');
    });
  });

  it('gruppiert nach Auslosung mit Zeitplan, Zeitpunkt und offenen Zuteilungen', async () => {
    const { view } = await mount();
    const sections = [...(view.shadowRoot?.querySelectorAll('.assignments section') ?? [])];
    expect(sections).toHaveLength(2);
    expect(sections[0]?.textContent).toContain('Wochenplan');
    expect(sections[0]?.textContent).toContain('4 offen');
    expect(sections[1]?.textContent).toContain('Ohne Zeitplan');
  });

  it('löscht eine Auslosung erst nach der Rückfrage', async () => {
    const { view, hass } = await mount();
    const [blocked, remove] =
      view.shadowRoot?.querySelectorAll('tw-confirm-action[label="Auslosung löschen"]') ?? [];
    const blockedButton = blocked?.shadowRoot?.querySelector('button');
    expect(blockedButton?.disabled).toBe(true);
    expect(blockedButton?.title).toBe('Nicht löschbar: 1 Aufgaben sind schon erledigt.');
    const host = remove as HTMLElement;
    await press(host, 'Auslosung löschen');
    expect(host.shadowRoot?.querySelector('tw-confirm-dialog')?.shadowRoot?.textContent).toContain(
      'Sie verschwindet auch aus Historie und Statistik',
    );
    expect(hass.messages.some((m) => m.type === WS_ROUND_DELETE)).toBe(false);
    await press(host, 'Abbrechen');
    expect(hass.messages.some((m) => m.type === WS_ROUND_DELETE)).toBe(false);
    await press(host, 'Auslosung löschen');
    await press(host, 'Löschen');
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ROUND_DELETE)).toEqual({
        type: WS_ROUND_DELETE,
        round_id: 'r2',
      });
    });
    // Die Statistik lädt erst nach dem Delta des Servers neu, und zwar nur einmal.
    expect(hass.calls.filter((call) => call === WS_STATISTICS_GET)).toHaveLength(1);
    hass.emit({ assignments: { upsert: [], remove: ['a1'] } });
    await vi.waitFor(() => {
      expect(hass.calls.filter((call) => call === WS_STATISTICS_GET)).toHaveLength(2);
    });
  });

  it('zeigt leere Zustände und Ladefehler', async () => {
    const hass = fakeHass();
    hass.snapshot = { ...hass.snapshot, assignments: [], schedules: [] };
    hass.replies.set(WS_HISTORY_LIST, { entries: [], next_offset: null });
    hass.replies.set(WS_STATISTICS_GET, new Error('x'));
    const { view } = await mount(hass);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Keine automatische Auslosung geplant.');
    });
    expect(text(view)).toContain('Keine offenen Zuteilungen.');
    expect(text(view)).toContain('Noch keine Aktivität.');
  });
});
