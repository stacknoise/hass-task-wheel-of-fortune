import { describe, expect, it } from 'vitest';

import { VIEW_TAGS } from '../constants/index.ts';
import { VIEW_LOADERS } from './registry.ts';

describe('Ansicht ohne Store', () => {
  it('rendert nichts, solange kein Stand da ist', async () => {
    await VIEW_LOADERS.history();
    const view = document.createElement(VIEW_TAGS.history);
    document.body.append(view);
    await (view as unknown as { updateComplete: Promise<boolean> }).updateComplete;
    expect(view.shadowRoot?.querySelector('tw-stat, p')).toBeNull();
  });
});
