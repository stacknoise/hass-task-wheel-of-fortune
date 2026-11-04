import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import '../components/index.ts';
import type { AreaNames } from '../state/index.ts';
import { roomsOf } from '../state/index.ts';

/** Räume einer Aufgabe als Marken; ohne Raum nichts. `unknown` steht für einen gelöschten Raum. */
export function roomTags(
  areas: AreaNames,
  areaIds: readonly string[] | null | undefined,
  unknown: string,
): TemplateResult | typeof nothing {
  const names = roomsOf(areas, areaIds, unknown);
  return names.length > 0
    ? html`${names.map((name) => html`<tw-room .name=${name}></tw-room> `)}`
    : nothing;
}
