import { describe, expect, it } from 'vitest';

import { PANEL_ELEMENT_NAME, PANEL_HEADING_CLASS } from './constants/index.ts';
import type { TaskWheelPanel } from './task-wheel-panel.ts';
import './task-wheel-panel.ts';

describe('task-wheel-panel', () => {
  it('rendert die Überschrift in der gewählten Sprache', async () => {
    const element = document.createElement(PANEL_ELEMENT_NAME) as TaskWheelPanel;
    element.language = 'de';
    document.body.append(element);
    await element.updateComplete;
    const heading = element.shadowRoot?.querySelector(`.${PANEL_HEADING_CLASS}`);
    expect(heading?.textContent).toBe('Aufgaben-Glücksrad');
  });
});
