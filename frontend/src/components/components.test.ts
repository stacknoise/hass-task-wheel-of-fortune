import { describe, expect, it } from 'vitest';

import { EVENT_CHIP_SELECT } from '../constants/index.ts';
import { initialOf } from './index.ts';
import type { TwAvatar, TwBadge, TwChips, TwRoom } from './index.ts';
import './index.ts';

async function mount<T extends HTMLElement & { updateComplete: Promise<boolean> }>(
  tag: string,
  props: Partial<T>,
): Promise<T> {
  const element = document.createElement(tag) as T;
  Object.assign(element, props);
  document.body.append(element);
  await element.updateComplete;
  return element;
}

describe('tw-avatar', () => {
  it('zeigt den Anfangsbuchstaben auf der Farbe der Person', async () => {
    const avatar = await mount<TwAvatar>('tw-avatar', { name: 'anna', color: '#c05600' });
    expect(avatar.shadowRoot?.textContent).toMatch(/^A/);
    expect(avatar.style.getPropertyValue('--avatar')).toBe('#c05600');
  });

  it('zerschneidet Emoji nicht', async () => {
    const avatar = await mount<TwAvatar>('tw-avatar', { name: ' 😀 Opa', color: '#c05600' });
    expect(avatar.shadowRoot?.textContent).toMatch(/^😀/);
    expect(initialOf('ärger')).toBe('Ä');
    expect(initialOf('   ')).toBe('');
  });

  it('bleibt ohne Namen leer', async () => {
    const avatar = await mount<TwAvatar>('tw-avatar', {});
    expect(avatar.shadowRoot?.textContent).toMatch(/^:host/);
  });
});

describe('tw-badge', () => {
  it('zeigt den Text im Ton', async () => {
    const badge = await mount<TwBadge>('tw-badge', { tone: 'success' });
    expect(badge.getAttribute('tone')).toBe('success');
    expect(badge.shadowRoot?.querySelector('slot')).not.toBeNull();
  });
});

describe('tw-room', () => {
  it('zeigt den Raum', async () => {
    const room = await mount<TwRoom>('tw-room', { name: 'Küche' });
    expect(room.shadowRoot?.textContent).toContain('Küche');
  });
  it('zeigt ohne Namen nichts', async () => {
    const room = await mount<TwRoom>('tw-room', {});
    expect(room.shadowRoot?.textContent).not.toContain('⌂');
  });
});

describe('tw-chips', () => {
  it('markiert die Wahl und meldet einen Klick', async () => {
    const chips = await mount<TwChips>('tw-chips', {
      items: [
        { id: 'a', label: 'Alle' },
        { id: 'b', label: 'Ben', color: '#123456' },
      ],
      selected: 'a',
    });
    const buttons = chips.shadowRoot?.querySelectorAll('button');
    expect(buttons?.[0]?.getAttribute('aria-pressed')).toBe('true');
    expect(buttons?.[1]?.querySelector('.dot')).not.toBeNull();
    let chosen = '';
    chips.addEventListener(EVENT_CHIP_SELECT, (event) => {
      chosen = (event as CustomEvent<string>).detail;
    });
    buttons?.[1]?.click();
    expect(chosen).toBe('b');
  });
});
