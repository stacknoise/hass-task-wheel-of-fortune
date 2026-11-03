import { describe, expect, it, vi } from 'vitest';

import {
  VIEW_TAGS,
  WS_ASSIGNMENT_COMPLETE,
  WS_ASSIGNMENT_SWAP,
  WS_HISTORY_LIST,
  WS_STATISTICS_GET,
} from '../constants/index.ts';
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
    expect(content).toContain('3 offen');
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
    expect(text(view)).toContain('1 offen');
    expect(view.shadowRoot?.querySelector('.assignments')?.textContent).not.toContain('Wochenplan');
  });

  it('erledigt eine Zuteilung und lädt Punkte und Aktivität neu', async () => {
    const { view, hass } = await mount();
    buttons(view, 'Erledigt')[0]?.click();
    await vi.waitFor(() => {
      expect(hass.messages.find((m) => m.type === WS_ASSIGNMENT_COMPLETE)).toEqual({
        type: WS_ASSIGNMENT_COMPLETE,
        assignment_id: 'a1',
      });
    });
    await vi.waitFor(() => {
      expect(hass.calls.filter((call) => call === WS_STATISTICS_GET)).toHaveLength(2);
    });
  });

  it('bietet nur erlaubte, nicht pausierte Personen zum Tausch an', async () => {
    const { view, hass } = await mount();
    buttons(view, 'Tauschen')[0]?.click();
    await view.updateComplete;
    const choice = view.shadowRoot?.querySelector('.swap');
    expect(choice?.textContent).toContain('Ben');
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

  it('sperrt das Tauschen ohne Joker oder wenn die Aufgabe es nicht erlaubt', async () => {
    const { view } = await mount();
    const swap = buttons(view, 'Tauschen');
    expect(swap[0]?.disabled).toBe(false);
    expect(swap[0]?.title).toBe('Joker übrig: 2');
    expect(swap[1]?.disabled).toBe(true);
    expect(swap[1]?.title).toBe('Diese Aufgabe darf nicht getauscht werden.');
    expect(swap[2]?.disabled).toBe(true);
  });

  it('klappt die Tauschauswahl wieder zu', async () => {
    const { view } = await mount();
    buttons(view, 'Tauschen')[0]?.click();
    await view.updateComplete;
    buttons(view, 'Abbrechen')[0]?.click();
    await view.updateComplete;
    expect(view.shadowRoot?.querySelector('.swap')).toBeNull();
  });

  it('zeigt einen Fehler, wenn die Aktion scheitert', async () => {
    const { view, hass } = await mount();
    hass.callWS = () => Promise.reject(new Error('nein'));
    buttons(view, 'Erledigt')[0]?.click();
    await vi.waitFor(() => {
      expect(text(view)).toContain('Die Aktion ist fehlgeschlagen.');
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
