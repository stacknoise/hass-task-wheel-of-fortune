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

  it('lässt Strg-, Cmd- und Mittelklick dem Browser, wählt aber beim einfachen Klick', async () => {
    const bar = document.createElement(COMPONENT_TAGS.tabBar) as Bar;
    bar.tabs = TABS;
    bar.active = 'a';
    document.body.append(bar);
    await bar.updateComplete;
    const selected = vi.fn();
    bar.addEventListener('tw-tab-select', selected);
    const link = bar.shadowRoot?.querySelectorAll('a')[1];
    const click = (init: MouseEventInit): MouseEvent => {
      const event = new MouseEvent('click', { bubbles: true, cancelable: true, ...init });
      link?.dispatchEvent(event);
      return event;
    };
    expect(click({ ctrlKey: true }).defaultPrevented).toBe(false);
    expect(click({ metaKey: true }).defaultPrevented).toBe(false);
    expect(click({ button: 1 }).defaultPrevented).toBe(false);
    expect(selected).not.toHaveBeenCalled();
    expect(click({}).defaultPrevented).toBe(true);
    expect(selected).toHaveBeenCalledOnce();
  });
});
