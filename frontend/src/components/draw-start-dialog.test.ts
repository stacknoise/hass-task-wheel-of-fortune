import { describe, expect, it, vi } from 'vitest';

import { EVENT_CONFIRM } from '../constants/index.ts';
import type { DrawWindowRequest } from '../state/index.ts';
import './draw-start-dialog.ts';
import type { TwDrawStartDialog } from './draw-start-dialog.ts';

const NOW = '2026-11-04T18:50:00+00:00';

async function open(nextRun: string): Promise<TwDrawStartDialog> {
  const dialog = document.createElement('tw-draw-start-dialog') as TwDrawStartDialog;
  dialog.language = 'de';
  dialog.now = NOW;
  dialog.nextRun = nextRun;
  document.body.append(dialog);
  await dialog.updateComplete;
  return dialog;
}

const confirm = (dialog: TwDrawStartDialog): HTMLButtonElement =>
  dialog.shadowRoot?.querySelector('.primary') as HTMLButtonElement;

describe('TwDrawStartDialog', () => {
  it('meldet bei einem nur manuellen Zeitplan Beginn und Dauer ohne Bestätigung', async () => {
    const dialog = await open('');
    const seen = vi.fn<(request: DrawWindowRequest) => void>();
    dialog.addEventListener(EVENT_CONFIRM, (event) => {
      seen((event as CustomEvent<DrawWindowRequest>).detail);
    });
    expect(dialog.shadowRoot?.querySelector('.warn')).toBeNull();
    confirm(dialog).click();
    expect(seen).toHaveBeenCalledWith({
      starts_at: NOW,
      duration: 7,
      duration_unit: 'day',
      replace_next: false,
    });
  });

  it('verlangt bei einem eingeplanten Zeitplan die Bestätigung des Vorziehens', async () => {
    const dialog = await open('2026-11-10T16:00:00+00:00');
    const seen = vi.fn<(request: DrawWindowRequest) => void>();
    dialog.addEventListener(EVENT_CONFIRM, (event) => {
      seen((event as CustomEvent<DrawWindowRequest>).detail);
    });
    expect(dialog.shadowRoot?.querySelector('.warn')).not.toBeNull();
    expect(confirm(dialog).disabled).toBe(true);
    const toggle = dialog.shadowRoot?.querySelector('.warn tw-toggle') as HTMLElement;
    toggle.dispatchEvent(
      new CustomEvent('tw-change', { detail: true, bubbles: true, composed: true }),
    );
    await dialog.updateComplete;
    expect(confirm(dialog).disabled).toBe(false);
    confirm(dialog).click();
    expect(seen.mock.calls[0]?.[0].replace_next).toBe(true);
  });

  it('braucht bei eigener Wahl ein Datum', async () => {
    const dialog = await open('');
    const select = dialog.shadowRoot?.querySelector('tw-select') as HTMLElement;
    select.dispatchEvent(
      new CustomEvent('tw-change', { detail: 'custom', bubbles: true, composed: true }),
    );
    await dialog.updateComplete;
    expect(confirm(dialog).disabled).toBe(true);
    const field = dialog.shadowRoot?.querySelector('tw-field') as HTMLElement;
    field.dispatchEvent(
      new CustomEvent('tw-change', {
        detail: '2026-11-05T10:00',
        bubbles: true,
        composed: true,
      }),
    );
    await dialog.updateComplete;
    expect(confirm(dialog).disabled).toBe(false);
  });
});
