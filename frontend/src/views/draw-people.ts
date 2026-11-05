import { html } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import '../components/index.ts';
import type { DrawState, PersonInfo } from '../state/index.ts';
import { waitingPersons } from './draw-rows.ts';

/** „Wer ist im Rad?“: die Personen, die noch auf eine Aufgabe warten, mit Avatar und Name. */
export function peopleList(
  title: string,
  state: DrawState,
  persons: ReadonlyMap<string, PersonInfo>,
): TemplateResult {
  return html`
    <div class="people">
      <span class="eyebrow">${title}</span>
      ${repeat(
        waitingPersons(state, persons),
        (person) => person.id,
        (person) => html`
          <div class="person">
            <tw-avatar name=${person.name} color=${person.color}></tw-avatar>
            <div>${person.name}</div>
          </div>
        `,
      )}
    </div>
  `;
}
