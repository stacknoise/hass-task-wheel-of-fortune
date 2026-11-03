import { describe, expect, it } from 'vitest';

import { COMPONENT_TAGS, CONFETTI_COUNT } from '../constants/index.ts';
import './confetti.ts';

describe('tw-confetti', () => {
  it('rendert die festgelegte Zahl Konfettistücke', async () => {
    const element = document.createElement(COMPONENT_TAGS.confetti) as HTMLElement & {
      updateComplete: Promise<boolean>;
    };
    document.body.append(element);
    await element.updateComplete;
    expect(element.shadowRoot?.querySelectorAll('span')).toHaveLength(CONFETTI_COUNT);
  });
});
