import { css, html, nothing, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { ABSENCE_KINDS, FORM_LIMITS, FORM_TAGS } from '../constants/index.ts';
import type { AbsenceKind } from '../constants/index.ts';
import { ABSENCE_BUILDERS } from '../state/index.ts';
import type { AbsenceWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import './chip-select.ts';
import './field.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import { toIds, toNumbers, weekOptions, weekdayOptions } from './options.ts';
import './select.ts';
import './stepper.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import './week-preview.ts';
import { defineOnce } from './define.ts';

/** Höchsthöhe der Regelliste (zwei einmalige Einträge ohne Scrollbalken); darüber scrollt sie, damit das Popup kompakt bleibt. */
const RULES_MAX_HEIGHT = '340px';

type Renderer = (absence: never, index: number) => TemplateResult;

/** Liste der Abwesenheitsregeln einer Person; die Vorschau der nächsten Wochen kommt von außen (`present`). */
export class TwAbsenceEditor extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    value: { attribute: false },
    today: { type: String },
    present: { attribute: false },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    stackStyles,
    css`
      .rules {
        display: grid;
        gap: var(--tw-space-field);
        max-height: ${unsafeCSS(RULES_MAX_HEIGHT)};
        overflow-y: auto;
      }
      .rule {
        display: grid;
        gap: var(--tw-space-field);
        padding: var(--tw-space-s) 0;
        border-bottom: 1px solid var(--tw-color-divider);
      }
      .head {
        display: flex;
        justify-content: space-between;
        align-items: end;
        gap: var(--tw-space-s);
      }
      button.plain {
        min-height: var(--tw-control-height);
        padding: 0 12px;
        border-radius: 18px;
        border: 1px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
    `,
  ];

  declare value: readonly AbsenceWire[];
  declare today: string;
  declare present: readonly boolean[];

  /** Eingabemaske je Art; die Tabelle ersetzt eine Verzweigung nach `kind`. */
  readonly #renderers: Readonly<Record<AbsenceKind, Renderer>> = {
    once: (absence: Extract<AbsenceWire, { kind: 'once' }>, index) => html`
      <div class="pair">
        <tw-field
          type="date"
          .label=${this.text('absence.start')}
          .value=${absence.start}
          @tw-change=${onChange<string>((start) => {
            this.replaceAt(this.value, index, { start });
          })}
        ></tw-field>
        <tw-field
          type="date"
          .label=${this.text('absence.end')}
          .value=${absence.end}
          @tw-change=${onChange<string>((end) => {
            this.replaceAt(this.value, index, { end });
          })}
        ></tw-field>
      </div>
    `,
    weekly_days: (absence: Extract<AbsenceWire, { kind: 'weekly_days' }>, index) => html`
      <tw-chip-select
        .label=${this.text('absence.weekdays')}
        .options=${weekdayOptions(this.language)}
        compact
        .selected=${toIds(absence.weekdays)}
        @tw-change=${onChange<string[]>((ids) => {
          this.replaceAt(this.value, index, { weekdays: toNumbers(ids) });
        })}
      ></tw-chip-select>
    `,
    week_rhythm: (absence: Extract<AbsenceWire, { kind: 'week_rhythm' }>, index) => html`
      <tw-stepper
        .label=${this.text('absence.cycle')}
        .value=${absence.cycle_weeks}
        .min=${FORM_LIMITS.rhythmCycle.min}
        .max=${FORM_LIMITS.rhythmCycle.max}
        @tw-change=${onChange<number>((cycle) => {
          this.replaceAt(this.value, index, {
            cycle_weeks: cycle,
            present_weeks: absence.present_weeks.filter((week) => week < cycle),
          });
        })}
      ></tw-stepper>
      <tw-chip-select
        .label=${this.text('absence.present_weeks')}
        .options=${weekOptions(absence.cycle_weeks, this.language)}
        .selected=${toIds(absence.present_weeks)}
        @tw-change=${onChange<string[]>((ids) => {
          this.replaceAt(this.value, index, { present_weeks: toNumbers(ids) });
        })}
      ></tw-chip-select>
      <tw-select
        .label=${this.text('absence.change_weekday')}
        .options=${weekdayOptions(this.language)}
        .value=${String(absence.change_weekday)}
        @tw-change=${onChange<string>((day) => {
          this.replaceAt(this.value, index, { change_weekday: Number(day) });
        })}
      ></tw-select>
      <tw-field
        type="date"
        .label=${this.text('absence.anchor')}
        .value=${absence.anchor}
        @tw-change=${onChange<string>((anchor) => {
          this.replaceAt(this.value, index, { anchor });
        })}
      ></tw-field>
    `,
  };

  constructor() {
    super();
    this.value = [];
    this.today = '';
    this.present = [];
  }

  protected override render(): TemplateResult {
    return html`
      ${this.value.length === 0 ? html`<p>${this.text('persons.no_absences')}</p>` : nothing}
      <div class="rules">
        ${repeat(
          this.value,
          (_, index) => index,
          (absence, index) => this.#rule(absence, index),
        )}
      </div>
      <div class="actions">
        <button
          type="button"
          class="plain"
          @click=${() => {
            this.#set([...this.value, ABSENCE_BUILDERS.once(this.today)]);
          }}
        >
          ${this.text('absence.add')}
        </button>
      </div>
      <tw-week-preview .language=${this.language} .present=${this.present}></tw-week-preview>
    `;
  }

  #rule(absence: AbsenceWire, index: number): TemplateResult {
    return html`
      <div class="rule">
        <div class="head">
          <tw-select
            .label=${this.text('persons.absences')}
            .options=${this.#kindOptions()}
            .value=${absence.kind}
            @tw-change=${onChange<AbsenceKind>((kind) => {
              this.#set(
                this.value.map((entry, at) =>
                  at === index ? ABSENCE_BUILDERS[kind](this.today) : entry,
                ),
              );
            })}
          ></tw-select>
          <button
            type="button"
            class="plain"
            @click=${() => {
              this.#set(this.value.filter((_entry, at) => at !== index));
            }}
          >
            ${this.text('form.remove')}
          </button>
        </div>
        ${this.#renderers[absence.kind](absence as never, index)}
      </div>
    `;
  }

  #kindOptions(): readonly { id: string; label: string }[] {
    return ABSENCE_KINDS.map((kind) => ({ id: kind, label: this.text(`absence.${kind}`) }));
  }

  #set(next: readonly AbsenceWire[]): void {
    emitChange(this, next);
  }
}

defineOnce(FORM_TAGS.absenceEditor, TwAbsenceEditor);
