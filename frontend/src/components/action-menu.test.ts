import { describe, expect, it } from 'vitest';

import { EVENT_ACTION } from '../constants/index.ts';
import { press } from './press.testing.ts';
import type { ActionItem, TwActionMenu } from './index.ts';
import './index.ts';

const ITEMS: readonly ActionItem[] = [
  { id: 'a', label: 'Eins' },
  { id: 'b', label: 'Zwei', question: 'Wirklich?' },
  { id: 'c', label: 'Drei', disabled: true, title: 'gesperrt' },
];

async function mountMenu(): Promise<{ menu: TwActionMenu; actions: string[] }> {
  const menu = document.createElement('tw-action-menu') as TwActionMenu;
  menu.language = 'de';
  menu.label = 'Aktionen';
  menu.items = ITEMS;
  const actions: string[] = [];
  menu.addEventListener(EVENT_ACTION, (event) => {
    actions.push((event as CustomEvent<string>).detail);
  });
  document.body.append(menu);
  await menu.updateComplete;
  return { menu, actions };
}

describe('tw-action-menu', () => {
  it('meldet einen Eintrag ohne Rückfrage sofort und schließt das Menü', async () => {
    const { menu, actions } = await mountMenu();
    await press(menu, 'Aktionen');
    await press(menu, 'Eins');
    expect(actions).toEqual(['a']);
    expect(menu.shadowRoot?.querySelector('.menu')).toBeNull();
  });

  it('fragt bei Einträgen mit Frage erst nach und meldet erst nach Bestätigung', async () => {
    const { menu, actions } = await mountMenu();
    await press(menu, 'Aktionen');
    await press(menu, 'Zwei');
    expect(actions).toEqual([]);
    expect(menu.shadowRoot?.querySelector('tw-confirm-dialog')).not.toBeNull();
    await press(menu, 'Zwei');
    expect(actions).toEqual(['b']);
    expect(menu.shadowRoot?.querySelector('tw-confirm-dialog')).toBeNull();
  });

  it('bricht die Rückfrage ab, sperrt Einträge und schließt mit Escape oder Klick daneben', async () => {
    const { menu, actions } = await mountMenu();
    await press(menu, 'Aktionen');
    const locked = [...(menu.shadowRoot?.querySelectorAll('.item') ?? [])][2] as HTMLButtonElement;
    expect(locked.disabled).toBe(true);
    expect(locked.title).toBe('gesperrt');
    await press(menu, 'Zwei');
    await press(menu, 'Abbrechen');
    expect(actions).toEqual([]);
    expect(menu.shadowRoot?.querySelector('tw-confirm-dialog')).toBeNull();
    await press(menu, 'Aktionen');
    menu.shadowRoot
      ?.querySelector('.menu')
      ?.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await menu.updateComplete;
    expect(menu.shadowRoot?.querySelector('.menu')).toBeNull();
    await press(menu, 'Aktionen');
    document.body.click();
    await menu.updateComplete;
    expect(menu.shadowRoot?.querySelector('.menu')).toBeNull();
  });
});
