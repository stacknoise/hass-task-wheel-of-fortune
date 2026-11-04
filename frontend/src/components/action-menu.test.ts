import { describe, expect, it, vi } from 'vitest';

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

  it('legt den Fokus ins Menü, wandert mit den Pfeiltasten und gibt ihn bei Escape zurück', async () => {
    const { menu } = await mountMenu();
    await press(menu, 'Aktionen');
    await menu.updateComplete;
    const items = [...(menu.shadowRoot?.querySelectorAll<HTMLElement>('.item') ?? [])];
    expect(menu.shadowRoot?.activeElement).toBe(items[0]);
    const key = (name: string): void => {
      menu.shadowRoot
        ?.querySelector('.menu')
        ?.dispatchEvent(new KeyboardEvent('keydown', { key: name, bubbles: true }));
    };
    key('ArrowDown');
    expect(menu.shadowRoot?.activeElement).toBe(items[1]);
    key('ArrowDown');
    expect(menu.shadowRoot?.activeElement).toBe(items[0]);
    key('End');
    expect(menu.shadowRoot?.activeElement).toBe(items[1]);
    key('ArrowUp');
    expect(menu.shadowRoot?.activeElement).toBe(items[0]);
    key('Escape');
    await menu.updateComplete;
    expect(menu.shadowRoot?.querySelector('.menu')).toBeNull();
    expect(menu.shadowRoot?.activeElement).toBe(menu.shadowRoot?.querySelector('.action'));
  });

  it('hört auf Klicks im Dokument nur, solange das Menü offen ist', async () => {
    const add = vi.spyOn(document, 'addEventListener');
    const remove = vi.spyOn(document, 'removeEventListener');
    const { menu } = await mountMenu();
    expect(add).not.toHaveBeenCalledWith('click', expect.anything());
    await press(menu, 'Aktionen');
    await menu.updateComplete;
    expect(add).toHaveBeenCalledWith('click', expect.anything());
    document.body.click();
    await menu.updateComplete;
    expect(remove).toHaveBeenCalledWith('click', expect.anything());
    add.mockRestore();
    remove.mockRestore();
  });
});
