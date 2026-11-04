import { afterEach, describe, expect, it, vi } from 'vitest';

import { EVENT_CANCEL } from '../constants/index.ts';
import type { TwConfirmDialog, TwDialog } from './index.ts';
import './index.ts';

async function mount<T extends HTMLElement & { updateComplete: Promise<boolean> }>(
  tag: string,
): Promise<T> {
  const element = document.createElement(tag) as T;
  Object.assign(element, { language: 'de', label: 'Titel', question: 'Wirklich?' });
  document.body.append(element);
  await element.updateComplete;
  return element;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe('modale Fenster', () => {
  it.each(['tw-dialog', 'tw-confirm-dialog'])(
    '%s öffnet sich als natives Modal und meldet Escape als Abbruch',
    async (tag) => {
      const element = await mount<TwDialog | TwConfirmDialog>(tag);
      const dialog = element.shadowRoot?.querySelector('dialog');
      expect(dialog?.hasAttribute('open')).toBe(true);
      const cancelled = vi.fn();
      element.addEventListener(EVENT_CANCEL, cancelled);
      const escape = new Event('cancel', { cancelable: true });
      dialog?.dispatchEvent(escape);
      expect(cancelled).toHaveBeenCalledOnce();
      expect(escape.defaultPrevented).toBe(true);
    },
  );

  it('schließt das Fenster beim Entfernen, damit der Fokus zurückkehrt', async () => {
    const element = await mount<TwDialog>('tw-dialog');
    const dialog = element.shadowRoot?.querySelector('dialog');
    element.remove();
    expect(dialog?.hasAttribute('open')).toBe(false);
  });

  it('beginnt die Rückfrage beim harmlosen Knopf', async () => {
    const element = await mount<TwConfirmDialog>('tw-confirm-dialog');
    const buttons = element.shadowRoot?.querySelectorAll('button');
    expect(buttons?.[0]?.hasAttribute('autofocus')).toBe(false);
    expect(buttons?.[1]?.hasAttribute('autofocus')).toBe(true);
  });
});
