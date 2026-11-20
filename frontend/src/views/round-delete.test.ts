import { html, render } from 'lit';
import { afterEach, describe, expect, it, vi } from 'vitest';

import '../components/index.ts';
import { roundDelete } from './round-delete.ts';
import type { RoundDeleteOptions } from './round-delete.ts';

const BASE: RoundDeleteOptions = {
  language: 'de',
  total: 4,
  done: 0,
  period: 2,
  newerDraw: false,
  automatic: false,
  busy: false,
  onConfirm: vi.fn(),
};

function mount(options: Partial<RoundDeleteOptions>): HTMLElement {
  const host = document.createElement('div');
  document.body.append(host);
  render(html`${roundDelete({ ...BASE, ...options })}`, host);
  return host.querySelector('tw-confirm-action') as HTMLElement;
}

afterEach(() => {
  document.body.replaceChildren();
});

describe('roundDelete', () => {
  it('erlaubt das Löschen der jüngsten Auslosung ohne erledigte Aufgaben', () => {
    const action = mount({});
    expect(action.getAttribute('blocked')).toBe('');
    expect(action.getAttribute('question')).toContain('Periode 3');
    expect(action.getAttribute('question')).not.toContain('nicht automatisch');
  });

  it('sperrt bei erledigten Aufgaben und bei einer neueren Auslosung', () => {
    expect(mount({ done: 2 }).getAttribute('blocked')).toBe(
      'Nicht löschbar: 2 Aufgaben sind schon erledigt.',
    );
    expect(mount({ newerDraw: true }).getAttribute('blocked')).toContain('neuere Auslosung');
  });

  it('weist bei automatischen Zeitplänen darauf hin, dass nichts nachgeholt wird', () => {
    const question = mount({ automatic: true }).getAttribute('question') ?? '';
    expect(question).toContain('nicht automatisch noch einmal ausgelost');
    expect(question).toContain('Periode 3');
    expect(question).toContain('übersprungen');
  });
});
