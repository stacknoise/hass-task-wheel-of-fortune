import { describe, expect, it, vi } from 'vitest';

import { VIEW_TAGS, WS_DECISIONS_LIST } from '../constants/index.ts';
import { DECISIONS, fakeHass, mountView, text } from './fixtures.testing.ts';
import { VIEW_LOADERS } from './registry.ts';

async function mount(hass = fakeHass()) {
  await VIEW_LOADERS.decisions();
  const view = await mountView(VIEW_TAGS.decisions, hass);
  await vi.waitFor(() => {
    expect(text(view)).toContain('Wochenplan');
  });
  return { view, hass };
}

function click(view: Element, label: string): void {
  [...(view.shadowRoot?.querySelectorAll('summary') ?? [])]
    .find((s) => s.textContent.includes(label))
    ?.click();
}

describe('Entscheidungslog', () => {
  it('zeigt Auslosung mit Zählern und Austausch mit Vermerk', async () => {
    const { view } = await mount();
    const content = text(view);
    expect(content).toContain('2 zugeteilt');
    expect(content).toContain('1 unvergeben');
    expect(content).toContain('Admin-Austausch');
    expect(content).toContain('vor dem Start');
    expect(content).toContain('Bad putzen → Anna');
    expect(content).toContain('Garage fegen → niemand');
  });

  it('erklärt je Person Rad, Chance und Ausschluss', async () => {
    const { view } = await mount();
    const content = text(view);
    expect(content).toContain('Chance 40 %, zufällig gezogen');
    expect(content).toContain('Chance 60 %');
    expect(content).toContain('Abwesend');
    expect(content).toContain('Einzige Person im Rad, direkt zugewiesen');
    expect(content).toContain('zukunft');
    expect(content).toContain('blieb unvergeben');
  });

  it('filtert nach Ergebnis und fragt Zeitplan und Person beim Backend', async () => {
    const { view, hass } = await mount();
    const chips = view.shadowRoot?.querySelector('tw-chips');
    [...(chips?.shadowRoot?.querySelectorAll('button') ?? [])]
      .find((b) => b.textContent.includes('Unvergeben'))
      ?.click();
    await view.updateComplete;
    expect(text(view)).not.toContain('Bad putzen → Anna');
    expect(text(view)).toContain('Garage fegen → niemand');
    const select = view.shadowRoot?.querySelectorAll('tw-select')[1];
    select?.dispatchEvent(new CustomEvent('tw-change', { detail: 'p1' }));
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({ type: WS_DECISIONS_LIST, person_id: 'p1' });
    });
  });

  it('lädt weitere Einträge nach', async () => {
    const { view, hass } = await mount();
    [...(view.shadowRoot?.querySelectorAll('button') ?? [])]
      .find((b) => b.textContent.includes('Weitere laden'))
      ?.click();
    await vi.waitFor(() => {
      expect(hass.messages.at(-1)).toMatchObject({ offset: DECISIONS.next_offset });
    });
    click(view, 'Wochenplan');
  });

  it('meldet leeres Log und Ladefehler', async () => {
    const hass = fakeHass();
    hass.replies.set(WS_DECISIONS_LIST, { entries: [], next_offset: null });
    await VIEW_LOADERS.decisions();
    const view = await mountView(VIEW_TAGS.decisions, hass);
    await vi.waitFor(() => {
      expect(text(view)).toContain('Keine Einträge');
    });
  });
});
