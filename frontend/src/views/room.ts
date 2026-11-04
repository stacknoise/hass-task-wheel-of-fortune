import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import '../components/index.ts';
import type { AreaNames } from '../state/index.ts';
import { roomOf } from '../state/index.ts';

/** Raum einer Aufgabe als Marke; ohne Raum nichts. `unknown` steht für einen gelöschten Raum. */
export function roomTag(
  areas: AreaNames,
  areaId: string | null | undefined,
  unknown: string,
): TemplateResult | typeof nothing {
  const name = roomOf(areas, areaId, unknown);
  return name ? html`<tw-room .name=${name}></tw-room>` : nothing;
}
