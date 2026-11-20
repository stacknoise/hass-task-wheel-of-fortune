import { nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { roomChips } from '../components/index.ts';
import type { AreaNames } from '../state/index.ts';
import { roomRefsOf } from '../state/index.ts';

/** Räume einer Aufgabe als Chips; ohne Raum nichts. `unknown` steht für einen gelöschten Raum. */
export function roomTags(
  areas: AreaNames,
  areaIds: readonly string[] | null | undefined,
  unknown: string,
): TemplateResult | typeof nothing {
  return roomChips(roomRefsOf(areas, areaIds, unknown));
}
