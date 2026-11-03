import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
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

  it('wird überall genutzt: keine Quelldatei ruft customElements.define direkt auf', () => {
    const root = join(import.meta.dirname, '..');
    const direct = readdirSync(root, { recursive: true, encoding: 'utf8' })
      .filter((name) => name.endsWith('.ts') && !name.endsWith('.test.ts'))
      .filter((name) => !name.endsWith('define.ts'))
      .filter((name) => readFileSync(join(root, name), 'utf8').includes('customElements.define('));
    expect(direct).toEqual([]);
  });
});
