import { describe, expect, it, vi } from 'vitest';

import { COMPONENT_TAGS } from '../constants/index.ts';
import './index.ts';

type Bar = HTMLElement & { updateComplete: Promise<boolean>; tabs: unknown; active: string };

const TABS = [
  { id: 'a', label: 'A', href: '#a' },
  { id: 'b', label: 'B', href: '#b' },
];

describe('Tab-Leiste', () => {
  it('holt beim Neuzeichnen nicht die ganze Seite nach oben', async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    const bar = document.createElement(COMPONENT_TAGS.tabBar) as Bar;
    bar.tabs = TABS;
    bar.active = 'a';
    document.body.append(bar);
    await bar.updateComplete;
    bar.tabs = [...TABS];
    bar.active = 'b';
    await bar.updateComplete;
    expect(scroll).not.toHaveBeenCalled();
  });
});
