import { afterEach, describe, expect, it, vi } from 'vitest';

import { ANIMATION_KINDS, STAGE_TAG, STAGE_TAGS } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import './index.ts';
import type { TwStage } from './stage.ts';

const SEGMENTS = [
  { id: 'a', label: 'Anna', color: '#c05600', chance: 0.6 },
  { id: 'b', label: 'Ben', color: '#1a5fd0', chance: 0.4 },
];

async function mount(kind?: AnimationKind): Promise<TwStage> {
  const stage = document.createElement(STAGE_TAG) as TwStage;
  if (kind) {
    stage.kind = kind;
  }
  stage.segments = SEGMENTS;
  stage.label = 'Auslosung';
  document.body.append(stage);
  await stage.updateComplete;
  return stage;
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.replaceChildren();
});

describe('tw-stage', () => {
  it('zeigt standardmäßig das Glücksrad', async () => {
    const stage = await mount();
    expect(stage.shadowRoot?.firstElementChild?.localName).toBe(STAGE_TAGS.wheel);
  });

  it.each(ANIMATION_KINDS)(
    'baut für „%s“ das Element der Registry mit Segmenten und Beschriftung',
    async (kind) => {
      const stage = await mount(kind);
      const element = stage.shadowRoot?.firstElementChild as HTMLElement & {
        segments: unknown;
        label: string;
      };
      expect(element.localName).toBe(STAGE_TAGS[kind]);
      expect(element.segments).toBe(SEGMENTS);
      expect(element.label).toBe('Auslosung');
    },
  );

  it('tauscht das Element beim Wechsel der Art und reicht neue Segmente weiter', async () => {
    const stage = await mount('wheel');
    stage.kind = 'spotlight';
    stage.segments = [SEGMENTS[0] as (typeof SEGMENTS)[number]];
    await stage.updateComplete;
    const element = stage.shadowRoot?.firstElementChild as HTMLElement & { segments: unknown[] };
    expect(element.localName).toBe(STAGE_TAGS.spotlight);
    expect(element.segments).toHaveLength(1);
  });

  it('gibt spinTo an das Element weiter', async () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }));
    const stage = await mount('wheel');
    const stopped = vi.fn();
    stage.shadowRoot?.firstElementChild?.addEventListener('tw-wheel-stop', stopped);
    await stage.spinTo('b');
    expect(stopped).toHaveBeenCalledOnce();
  });
});
