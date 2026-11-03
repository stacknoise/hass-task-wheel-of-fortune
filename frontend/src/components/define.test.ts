import { describe, expect, it } from 'vitest';

import { defineOnce } from './define.ts';

describe('defineOnce', () => {
  it('meldet ein Element nur einmal an und ignoriert eine zweite Anmeldung', () => {
    class First extends HTMLElement {}
    class Second extends HTMLElement {}
    defineOnce('tw-define-once-test', First);
    expect(() => {
      defineOnce('tw-define-once-test', Second);
    }).not.toThrow();
    expect(customElements.get('tw-define-once-test')).toBe(First);
  });
});
