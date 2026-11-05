import { html } from 'lit';
import type { TemplateResult } from 'lit';
import { styleMap } from 'lit/directives/style-map.js';

import '../components/index.ts';
import type { PersonInfo } from '../state/index.ts';

/** Eigenschaft der Personenfarbe am Chip; das Stylesheet leitet Rand und Tönung davon ab. */
const PERSON_COLOR_VAR = '--tw-person-color';

/** Auffälliger Chip mit Marke und Namen der Person, der die Aufgabe zugeteilt wurde. */
export function winnerChip(person: PersonInfo): TemplateResult {
  return html`<span class="winner" style=${styleMap({ [PERSON_COLOR_VAR]: person.color || null })}>
    <tw-avatar name=${person.name} color=${person.color}></tw-avatar>
    <strong>${person.name}</strong>
  </span>`;
}
