import { css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { tasksOf } from '../api/index.ts';
import type { PersonWire, Snapshot } from '../api/index.ts';
import { onChange } from '../components/index.ts';
import '../components/index.ts';
import {
  DEFAULT_LOAD,
  FORM_LIMITS,
  LOADS,
  NOTIFY_PREFIX,
  PERSON_COLORS,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { Load } from '../constants/index.ts';
import { dayOf } from '../state/index.ts';
import type { AbsenceWire } from '../state/index.ts';
import { ConfigView } from './config-view.ts';
import type { ConfigTexts } from './config-view.ts';

interface PersonDraft {
  readonly name: string;
  readonly color: string;
  readonly load: Load;
  readonly absences: readonly AbsenceWire[];
  readonly notifyTarget: string;
}

const TEXTS: ConfigTexts = { add: 'persons.add', create: 'persons.new', edit: 'persons.edit' };

/** Personen: Farbe, Belastbarkeit, Anwesenheit mit Vorschau und Benachrichtigung. */
export class PersonsView extends ConfigView<PersonWire, PersonDraft> {
  static override styles = [
    ...ConfigView.styles,
    css`
      .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        color: #fff;
        font-weight: 700;
      }
      .name {
        font-weight: 500;
        margin-left: var(--tw-space-s);
      }
      .swatches {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      .swatch {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 2px solid transparent;
        cursor: pointer;
      }
      .swatch[aria-pressed='true'] {
        border-color: var(--tw-color-text);
      }
    `,
  ];

  protected readonly resource = 'person';
  protected readonly collection = 'persons';
  protected readonly texts = TEXTS;

  protected blank(): PersonDraft {
    return {
      name: '',
      color: PERSON_COLORS[0],
      load: DEFAULT_LOAD,
      absences: [],
      notifyTarget: '',
    };
  }

  protected draftOf(person: PersonWire): PersonDraft {
    return {
      name: person.name,
      color: person.color,
      load: person.load,
      absences: person.absences,
      notifyTarget: person.notify_target ?? '',
    };
  }

  protected payload(draft: PersonDraft): object {
    return {
      name: draft.name,
      color: draft.color,
      load: draft.load,
      absences: draft.absences,
      notify_target: draft.notifyTarget.trim() || null,
    };
  }

  protected card(person: PersonWire, snapshot: Snapshot): TemplateResult {
    const tasks = tasksOf(snapshot).filter((task) => task.allowed.includes(person.id)).length;
    return html`
      <span class="avatar" style="background:${person.color}">${person.name.slice(0, 1)}</span>
      <span class="name">${person.name}</span>
      <div class="muted">
        ${this.text(`load.${person.load}`)} · ${this.text('persons.tasks')}: ${tasks}
      </div>
    `;
  }

  protected form(draft: PersonDraft, snapshot: Snapshot): TemplateResult {
    return html`
      ${this.nameField(draft.name, (name) => {
        this.patch({ name });
      })}
      ${this.#colors(draft.color)}
      <tw-segmented
        .label=${this.text('persons.load')}
        .options=${LOADS.map((load) => ({ id: load, label: this.text(`load.${load}`) }))}
        .value=${draft.load}
        @tw-change=${onChange<Load>((load) => {
          this.patch({ load });
        })}
      ></tw-segmented>
      <tw-absence-editor
        .language=${this.language}
        .today=${dayOf(snapshot.now)}
        .value=${draft.absences}
        @tw-change=${onChange<readonly AbsenceWire[]>((absences) => {
          this.patch({ absences });
        })}
      ></tw-absence-editor>
      <tw-field
        .label=${this.text('persons.notify_target')}
        .value=${draft.notifyTarget}
        .placeholder=${NOTIFY_PREFIX}
        .maxlength=${FORM_LIMITS.notifyMax}
        .error=${this.fieldError('notify_target')}
        @tw-change=${onChange<string>((notifyTarget) => {
          this.patch({ notifyTarget });
        })}
      ></tw-field>
    `;
  }

  #colors(selected: string): TemplateResult {
    return html`
      <div>
        <span class="label">${this.text('persons.color')}</span>
        <div class="swatches">
          ${PERSON_COLORS.map(
            (color) => html`
              <button
                type="button"
                class="swatch"
                style="background:${color}"
                aria-label=${color}
                aria-pressed=${color === selected ? 'true' : 'false'}
                @click=${() => {
                  this.patch({ color });
                }}
              ></button>
            `,
          )}
        </div>
      </div>
    `;
  }
}

customElements.define(VIEW_TAGS.persons, PersonsView);
