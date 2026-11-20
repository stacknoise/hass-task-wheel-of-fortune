import { css, html, nothing, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import {
  ENTRY_ROWS_VISIBLE,
  FORM_LIMITS,
  FORM_TAGS,
  INTERVAL_UNIT_HOURS,
} from '../constants/index.ts';
import type { EntryMode } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { newEntry } from '../state/index.ts';
import type { EntryWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import type { ChipOption } from './chip-select.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import './room.ts';
import './stepper.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';
import { describeSpan } from './summaries.ts';
import './toggle.ts';
import { defineOnce } from './define.ts';

/** Höhe einer Zeile in `em`; die Liste zeigt `ENTRY_ROWS_VISIBLE` Zeilen, danach erscheint die Bildlaufleiste. */
const ROW_HEIGHT_EM = 6.5;

/**
 * Die Aufgaben eines Zeitplans und wie häufig sie vorkommen: je Aufgabe „mindestens n× je Lauf“ oder
 * „jede Auslosung“. Meldet die Liste der Einträge in der Reihenfolge der Aufgaben.
 */
export class TwEntryEditor extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    tasks: { attribute: false },
    value: { attribute: false },
    runDays: { type: Number },
    error: { type: String },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    formStyles,
    stackStyles,
    css`
      .rows {
        display: grid;
        gap: var(--tw-space-s);
        max-height: ${unsafeCSS(String(ENTRY_ROWS_VISIBLE * ROW_HEIGHT_EM))}em;
        overflow-y: auto;
      }
      .row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: var(--tw-space-s) var(--tw-space-m);
        padding: var(--tw-space-s) var(--tw-space-m);
        border: 1px solid var(--tw-color-divider);
        border-radius: 8px;
      }
      .row.on {
        border-color: var(--tw-color-primary);
      }
      .name {
        display: grid;
        gap: var(--tw-space-xs);
        justify-items: start;
      }
      .detail {
        grid-column: 1 / -1;
        display: flex;
        flex-wrap: wrap;
        align-items: end;
        gap: var(--tw-space-m);
      }
    `,
  ];

  declare tasks: readonly ChipOption[];
  declare value: readonly EntryWire[];
  /** Länge eines Laufs in Tagen, für die Umrechnung in einen ungefähren Abstand. */
  declare runDays: number;
  declare error: string;

  constructor() {
    super();
    this.tasks = [];
    this.value = [];
    this.runDays = 1;
    this.error = '';
  }

  protected override render(): TemplateResult {
    return html`
      <div>
        <span class="label">${this.text('entries.title')}</span>
        <div class="rows" role="group" aria-label=${this.text('entries.title')}>
          ${repeat(
            this.tasks,
            (task) => task.id,
            (task) =>
              this.#row(
                task,
                this.value.find((entry) => entry.task_id === task.id),
              ),
          )}
        </div>
        ${this.error ? html`<div class="error">${this.error}</div>` : nothing}
      </div>
      <span class="hint">${this.text('entries.hint')}</span>
    `;
  }

  #row(task: ChipOption, entry: EntryWire | undefined): TemplateResult {
    return html`<div class="row ${entry ? 'on' : ''}">
      <div class="name">
        <tw-toggle
          .label=${task.label}
          .checked=${entry !== undefined}
          @tw-change=${onChange<boolean>((on) => {
            this.#select(task.id, on);
          })}
        ></tw-toggle>
        ${(task.rooms ?? []).map((name) => html`<tw-room .name=${name}></tw-room> `)}
      </div>
      ${entry ? this.#detail(entry) : nothing}
    </div>`;
  }

  #detail(entry: EntryWire): TemplateResult {
    const every = entry.mode === 'every_draw';
    return html`<div class="detail">
      ${
        every
          ? html`<span class="muted">${this.text('entries.every_draw_hint')}</span>`
          : html`<tw-stepper
                .label=${this.text('entries.min_count')}
                .value=${entry.min_count}
                .min=${FORM_LIMITS.minCount.min}
                .max=${FORM_LIMITS.minCount.max}
                @tw-change=${onChange<number>((min_count) => {
                  this.#patch(entry.task_id, { min_count });
                })}
              ></tw-stepper>
              <span class="muted">${this.#approx(entry.min_count)}</span>`
      }
      <tw-toggle
        .label=${this.text('entries.every_draw')}
        .checked=${every}
        @tw-change=${onChange<boolean>((on) => {
          this.#patch(entry.task_id, {
            mode: (on ? 'every_draw' : 'min_count') satisfies EntryMode,
          });
        })}
      ></tw-toggle>
    </div>`;
  }

  /** Ungefährer Abstand: `n`× in einem Lauf. */
  #approx(count: number): string {
    const hours = Math.round((this.runDays * INTERVAL_UNIT_HOURS.day) / count);
    return translate('entries.approx', this.language, {
      span: describeSpan(hours, this.language),
    });
  }

  #select(taskId: string, on: boolean): void {
    const kept = this.value.filter((entry) => entry.task_id !== taskId);
    const next = on ? [...kept, newEntry(taskId)] : kept;
    const order = new Map(this.tasks.map((task, index) => [task.id, index]));
    emitChange(
      this,
      [...next].sort((a, b) => (order.get(a.task_id) ?? 0) - (order.get(b.task_id) ?? 0)),
    );
  }

  #patch(taskId: string, patch: Partial<EntryWire>): void {
    this.replaceAt(
      this.value,
      this.value.findIndex((entry) => entry.task_id === taskId),
      patch,
    );
  }
}

defineOnce(FORM_TAGS.entryEditor, TwEntryEditor);
