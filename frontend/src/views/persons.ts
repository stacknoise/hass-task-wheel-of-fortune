import { css, html, unsafeCSS } from 'lit';
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
  DEFAULT_PERSON_COLOR,
  PERSON_COLOR_COLUMNS,
  PERSON_COLORS,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { Load } from '../constants/index.ts';
import { AsyncValue, allowsPerson, dayOf } from '../state/index.ts';
import type { AbsenceWire } from '../state/index.ts';
import { ConfigView } from './config-view.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

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
      tw-avatar {
        --tw-avatar-size: 40px;
        --tw-avatar-font: 1em;
      }
      .name {
        font-weight: 500;
        margin-left: var(--tw-space-s);
      }
      .swatches {
        display: grid;
        grid-template-columns: repeat(${unsafeCSS(PERSON_COLOR_COLUMNS)}, minmax(0, 32px));
        gap: var(--tw-space-s);
      }
      .swatch {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 50%;
        border: 2px solid transparent;
        cursor: pointer;
      }
      .swatch[aria-pressed='true'] {
        border-color: var(--tw-color-text);
      }
    `,
  ];

  /** Anwesenheit der nächsten Wochen für die Regeln im Entwurf; gerechnet wird im Backend. */
  readonly #preview = new AsyncValue<readonly boolean[]>(this);
  #previewFor: readonly AbsenceWire[] | undefined;

  protected readonly resource = 'person';
  protected readonly collection = 'persons';
  protected readonly texts = TEXTS;

  protected override willUpdate(): void {
    super.willUpdate();
    const absences = this._draft?.absences;
    const client = this.store.client;
    if (absences !== undefined && client !== undefined && absences !== this.#previewFor) {
      this.#previewFor = absences;
      void this.#preview.run(() => client.availabilityPreview(absences));
    }
  }

  protected blank(): PersonDraft {
    return {
      name: '',
      color: DEFAULT_PERSON_COLOR,
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
    const tasks = tasksOf(snapshot).filter((task) =>
      allowsPerson(new Set(task.allowed), person.id),
    ).length;
    return html`
      <tw-avatar name=${person.name} color=${person.color}></tw-avatar>
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
      <tw-select
        .label=${this.text('persons.load')}
        .options=${LOADS.map((load) => ({ id: load, label: this.text(`load.${load}`) }))}
        .value=${draft.load}
        @tw-change=${onChange<Load>((load) => {
          this.patch({ load });
        })}
      ></tw-select>
      <tw-absence-editor
        .language=${this.language}
        .today=${dayOf(snapshot.now)}
        .value=${draft.absences}
        .present=${this.#preview.value ?? []}
        @tw-change=${onChange<readonly AbsenceWire[]>((absences) => {
          this.patch({ absences });
        })}
      ></tw-absence-editor>
      <tw-field
        .label=${this.text('persons.notify_target')}
        .value=${draft.notifyTarget}
        .placeholder=${NOTIFY_PREFIX}
        .maxlength=${FORM_LIMITS.notifyMax}
        .suggestions=${this.store.client?.notifyTargets() ?? []}
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

defineOnce(VIEW_TAGS.persons, PersonsView);
