import { css, html, nothing, unsafeCSS } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import {
  DIALOG_COMPACT_MAX_WIDTH,
  ENTRY_FILTERS,
  FORM_LIMITS,
  FORM_TAGS,
  INTERVAL_UNIT_HOURS,
} from '../constants/index.ts';
import type { EntryFilter, EntryMode } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { newEntry } from '../state/index.ts';
import type { EntryWire } from '../state/index.ts';
import { emitChange, onChange } from './change.ts';
import type { ChipOption } from './chip-select.ts';
import { formStyles, stackStyles } from './formStyles.ts';
import { LocalizedElement } from './localized.ts';
import { roomChips } from './room.ts';
import './segmented.ts';
import './stepper.ts';
import { baseStyles, tokenStyles, viewStyles } from './styles.ts';
import { describeSpan } from './summaries.ts';
import './toggle.ts';
import { defineOnce } from './define.ts';

/**
 * Die Aufgaben eines Zeitplans und wie häufig sie vorkommen: je Aufgabe „mindestens n× je Lauf“ oder
 * „jede Auslosung“. Mit Suche, Filter und Raumfilter für lange Listen; die Liste scrollt mit dem
 * Dialog, die Werkzeugleiste bleibt oben stehen. Meldet die Liste der Einträge in der Reihenfolge der Aufgaben.
 */
export class TwEntryEditor extends LocalizedElement {
  static override properties = {
    ...LocalizedElement.properties,
    tasks: { attribute: false },
    value: { attribute: false },
    runDays: { type: Number },
    error: { type: String },
    query: { type: String },
    _search: { state: true },
    _filter: { state: true },
    _room: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    formStyles,
    stackStyles,
    css`
      :host {
        gap: 0;
      }
      .tools {
        position: sticky;
        top: calc(-1 * var(--tw-space-m));
        z-index: 1;
        display: grid;
        gap: var(--tw-space-s);
        margin: calc(-1 * var(--tw-space-m)) calc(-1 * var(--tw-space-m)) 0;
        padding: var(--tw-space-m) var(--tw-space-m) var(--tw-space-s);
        background: var(--tw-color-surface);
        border-bottom: 1px solid var(--tw-color-divider);
      }
      input[type='search'] {
        width: 100%;
      }
      .rooms {
        display: flex;
        gap: var(--tw-space-s);
        overflow-x: auto;
      }
      .rooms button {
        flex: none;
        padding: 0 var(--tw-space-m);
        border: 1px solid var(--tw-color-divider);
        border-radius: 1em;
        background: none;
        cursor: pointer;
      }
      .rooms button[aria-pressed='true'] {
        background: var(--tw-color-primary);
        border-color: var(--tw-color-primary);
        color: var(--tw-color-on-primary);
      }
      .row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: center;
        gap: var(--tw-space-xs) var(--tw-space-m);
        padding: var(--tw-space-xs) 0;
        border-bottom: 1px solid var(--tw-color-divider);
      }
      .name {
        display: grid;
        justify-items: start;
        min-width: 0;
      }
      .detail {
        display: grid;
        grid-template-columns: 10em 7.5em auto;
        align-items: center;
        gap: var(--tw-space-s);
      }
      .approx {
        text-align: right;
        font-size: 0.85em;
        color: var(--tw-color-text-muted);
      }
      .every {
        min-height: 32px;
        padding: 0 var(--tw-space-s);
        border: 1px solid var(--tw-color-divider);
        border-radius: 1em;
        background: none;
        cursor: pointer;
      }
      .every[aria-pressed='true'] {
        background: var(--tw-color-primary);
        border-color: var(--tw-color-primary);
        color: var(--tw-color-on-primary);
      }
      @media (max-width: ${unsafeCSS(DIALOG_COMPACT_MAX_WIDTH)}px) {
        .detail {
          grid-template-columns: 7.5em auto;
        }
        .approx {
          display: none;
        }
      }
    `,
  ];

  declare tasks: readonly ChipOption[];
  declare value: readonly EntryWire[];
  /** Länge eines Laufs in Tagen, für die Umrechnung in einen ungefähren Abstand. */
  declare runDays: number;
  declare error: string;
  /** Vorgegebener Suchtext (zum Beispiel beim Sprung von einem Hinweis zur Aufgabe). */
  declare query: string;
  declare _search: string;
  declare _filter: EntryFilter;
  declare _room: string;

  constructor() {
    super();
    this.tasks = [];
    this.value = [];
    this.runDays = 1;
    this.error = '';
    this.query = '';
    this._search = '';
    this._filter = 'all';
    this._room = '';
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (changed.has('query')) {
      this._search = this.query;
    }
  }

  protected override render(): TemplateResult {
    const shown = this.#visible();
    return html`
      ${this.#tools()}
      <div role="group" aria-label=${this.text('entries.title')}>
        ${
          shown.length === 0
            ? html`<p class="empty">${this.text('entries.none')}</p>`
            : repeat(
                shown,
                (task) => task.id,
                (task) =>
                  this.#row(
                    task,
                    this.value.find((entry) => entry.task_id === task.id),
                  ),
              )
        }
      </div>
      ${this.error ? html`<div class="error">${this.error}</div>` : nothing}
      <span class="hint">${this.text('entries.hint')}</span>
    `;
  }

  /** Aufgaben, die zu Suche, Filter und Raum passen. */
  #visible(): readonly ChipOption[] {
    const needle = this._search.trim().toLowerCase();
    const selected = new Set(this.value.map((entry) => entry.task_id));
    return this.tasks.filter((task) => {
      const rooms = task.rooms ?? [];
      const filtered =
        this._filter === 'all' || (this._filter === 'selected') === selected.has(task.id);
      const inRoom = this._room === '' || rooms.some((room) => room.name === this._room);
      const found =
        needle === '' ||
        [task.label, ...rooms.map((room) => room.name)].some((text) =>
          text.toLowerCase().includes(needle),
        );
      return filtered && inRoom && found;
    });
  }

  #tools(): TemplateResult {
    const count = this.value.length;
    const counts: Readonly<Record<EntryFilter, number>> = {
      all: this.tasks.length,
      selected: count,
      open: this.tasks.length - count,
    };
    const filters = ENTRY_FILTERS.map((id) => ({
      id,
      label: `${this.text(`entries.filter.${id}` satisfies TextKey)} ${String(counts[id])}`,
    }));
    const rooms = [
      ...new Set(this.tasks.flatMap((task) => (task.rooms ?? []).map((room) => room.name))),
    ].sort((a, b) => a.localeCompare(b));
    return html`<div class="tools">
      <input
        type="search"
        class="control"
        .value=${this._search}
        placeholder=${this.text('entries.search')}
        aria-label=${this.text('entries.search')}
        @input=${(event: Event) => {
          this._search = (event.target as HTMLInputElement).value;
        }}
      />
      <tw-segmented
        .options=${filters}
        .value=${this._filter}
        @tw-change=${onChange<EntryFilter>((filter) => {
          this._filter = filter;
        })}
      ></tw-segmented>
      ${this.#roomFilter(rooms)}
    </div>`;
  }

  /** Raumfilter als Chips in einer Zeile (scrollt seitlich); ohne Räume entfällt er. */
  #roomFilter(rooms: readonly string[]): TemplateResult | typeof nothing {
    return rooms.length === 0
      ? nothing
      : html`<div class="rooms" role="group" aria-label=${this.text('tasks.area')}>
          ${rooms.map(
            (room) =>
              html`<button
                type="button"
                aria-pressed=${this._room === room ? 'true' : 'false'}
                @click=${() => {
                  this._room = this._room === room ? '' : room;
                }}
              >
                ${room}
              </button>`,
          )}
        </div>`;
  }

  #row(task: ChipOption, entry: EntryWire | undefined): TemplateResult {
    return html`<div class="row">
      <div class="name">
        <tw-toggle
          .label=${task.label}
          .checked=${entry !== undefined}
          @tw-change=${onChange<boolean>((on) => {
            this.#select(task.id, on);
          })}
        ></tw-toggle>
        <span>${roomChips(task.rooms ?? [])}</span>
      </div>
      ${entry ? this.#detail(entry) : nothing}
    </div>`;
  }

  /** Abstand, Zähler und „Jede“ stehen in festen Spalten, damit sie in allen Zeilen untereinander ausgerichtet sind. */
  #detail(entry: EntryWire): TemplateResult {
    const every = entry.mode === 'every_draw';
    return html`<div class="detail">
      <span class="approx">
        ${every ? this.text('entries.every_short') : this.#approx(entry.min_count)}
      </span>
      ${
        every
          ? html`<span></span>`
          : html`<tw-stepper
              compact
              .label=${this.text('entries.min_count')}
              .value=${entry.min_count}
              .min=${FORM_LIMITS.minCount.min}
              .max=${FORM_LIMITS.minCount.max}
              @tw-change=${onChange<number>((min_count) => {
                this.#patch(entry.task_id, { min_count });
              })}
            ></tw-stepper>`
      }
      <button
        type="button"
        class="every"
        title=${this.text('entries.every_short')}
        aria-pressed=${every ? 'true' : 'false'}
        @click=${() => {
          this.#patch(entry.task_id, {
            mode: (every ? 'min_count' : 'every_draw') satisfies EntryMode,
          });
        }}
      >
        ${this.text('entries.every_chip')}
      </button>
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
