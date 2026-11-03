import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { modelsOf } from '../api/index.ts';
import type { ApiClient, AssignmentObject, RoundObject } from '../api/index.ts';
import { baseStyles, tokenStyles, viewStyles } from '../components/index.ts';
import '../components/index.ts';
import {
  CSV_FILE_NAME,
  CSV_MIME,
  EVENT_CHIP_SELECT,
  EXPORT_MAX_PAGES,
  EXPORT_PAGE_SIZE,
  FILTER_ALL,
  HISTORY_PAGE_SIZE,
  STATUS_TONES,
  VIEW_TAGS,
} from '../constants/index.ts';
import { formatDateTime, formatPercent } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';
import { AsyncValue, StoreController, indexById } from '../state/index.ts';
import { personChips } from './person-chips.ts';
import { buildCsv } from './csv.ts';
import { roundDelete } from './round-delete.ts';
import { downloadText } from './download.ts';
import { closedCount, csvRows, doneCount, originText } from './history-model.ts';
import type { HistoryLookups } from './history-model.ts';

interface Loaded {
  readonly rounds: readonly RoundObject[];
  readonly next: number | null;
}

/** Historie: Runden aufklappbar, Filter nach Person, Nachladen und CSV-Export. */
export class TwHistoryView extends LitElement {
  static override properties = {
    language: { type: String },
    _filter: { state: true },
    _open: { state: true },
    _exporting: { state: true },
    _exportFailed: { state: true },
    _busy: { state: true },
    _deleteFailed: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      .round-head {
        display: flex;
        width: 100%;
        align-items: center;
        gap: var(--tw-space-m);
        padding: 0;
        border: none;
        background: transparent;
        color: inherit;
        font: inherit;
        text-align: left;
        cursor: pointer;
      }
      .chevron {
        transition: transform var(--tw-duration);
      }
      [aria-expanded='true'] .chevron {
        transform: rotate(180deg);
      }
      .table {
        margin-top: var(--tw-space-s);
        border-top: 1px solid var(--tw-color-divider);
      }
      .person {
        display: inline-flex;
        align-items: center;
        gap: var(--tw-space-s);
      }
    `,
  ];

  declare language: string;
  declare _filter: string;
  declare _open: ReadonlySet<string>;
  declare _exporting: boolean;
  declare _exportFailed: boolean;
  declare _busy: boolean;
  declare _deleteFailed: boolean;

  readonly #store = new StoreController(this);
  readonly #data = new AsyncValue<Loaded>(this);
  #started = false;

  constructor() {
    super();
    this.language = '';
    this._filter = FILTER_ALL;
    this._open = new Set();
    this._exporting = false;
    this._exportFailed = false;
    this._busy = false;
    this._deleteFailed = false;
    this.addEventListener(EVENT_CHIP_SELECT, (event) => {
      this._filter = (event as CustomEvent<string>).detail;
      this.#load(false);
    });
  }

  protected override willUpdate(): void {
    if (this.#store.client && !this.#started) {
      this.#started = true;
      this.#load(false);
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    if (!snapshot) {
      return nothing;
    }
    const persons = modelsOf(snapshot, 'persons');
    const lookups: HistoryLookups = {
      persons: indexById(persons),
      tasks: indexById(modelsOf(snapshot, 'tasks')),
      schedules: indexById(modelsOf(snapshot, 'schedules')),
    };
    const chips = personChips(persons, this.#text('overview.filterAll'));
    return html`
      <div class="row card">
        <span class="muted">${this.#text('history.filter')}</span>
        <tw-chips
          class="grow"
          .items=${chips}
          selected=${this._filter}
          label=${this.#text('history.filter')}
        ></tw-chips>
        <button
          type="button"
          class="action"
          ?disabled=${this._exporting}
          @click=${() => {
            this.#export(lookups);
          }}
        >
          ${this.#text('history.export')}
        </button>
      </div>
      ${
        this._exportFailed
          ? html`<p class="error" role="alert">${this.#text('history.exportError')}</p>`
          : nothing
      }
      ${
        this._deleteFailed
          ? html`<p class="error" role="alert">${this.#text('overview.actionError')}</p>`
          : nothing
      }
      ${this.#body(lookups)}
    `;
  }

  #text(key: TextKey, params?: TextParams): string {
    return translate(key, this.language, params);
  }

  #body(lookups: HistoryLookups): TemplateResult {
    const { status, value } = this.#data;
    if (status === 'error') {
      return html`<p class="error" role="alert">${this.#text('common.loadError')}</p>`;
    }
    if (!value) {
      return html`<p class="empty">${this.#text('common.loading')}</p>`;
    }
    if (value.rounds.length === 0) {
      return html`<p class="empty">${this.#text('history.empty')}</p>`;
    }
    return html`
      ${repeat(
        value.rounds,
        (round) => round.id,
        (round) => this.#round(round, lookups),
      )}
      ${
        value.next === null
          ? nothing
          : html`<button
              type="button"
              class="action"
              ?disabled=${status === 'loading'}
              @click=${() => {
                this.#load(true);
              }}
            >
              ${this.#text('history.more')}
            </button>`
      }
    `;
  }

  #round(round: RoundObject, lookups: HistoryLookups): TemplateResult {
    const open = this._open.has(round.id);
    const schedule = lookups.schedules.get(round.schedule_id)?.name;
    const text = (key: TextKey): string => this.#text(key);
    return html`
      <section class="card">
        <button
          type="button"
          class="round-head"
          aria-expanded=${open ? 'true' : 'false'}
          @click=${() => {
            this.#toggle(round.id);
          }}
        >
          <span class="grow">
            <strong>${schedule ?? this.#text('common.unknownSchedule')}</strong><br />
            <span class="muted"
              >${formatDateTime(round.started_at, this.language)} ·
              ${originText(round.origin, text)}</span
            >
          </span>
          <span class="muted fixed"
            >${this.#text('history.summary', {
              done: doneCount(round.assignments),
              total: round.assignments.length,
            })}</span
          >
          <span class="chevron" aria-hidden="true">▾</span>
        </button>
        ${open ? this.#table(round, lookups) : nothing}
        ${roundDelete({
          language: this.language,
          total: round.assignments.length,
          closed: closedCount(round.assignments),
          busy: this._busy,
          onConfirm: () => {
            this.#delete(round.id);
          },
        })}
      </section>
    `;
  }

  #table(round: RoundObject, lookups: HistoryLookups): TemplateResult {
    return html`
      <div class="scroll table">
        <table>
          <thead>
            <tr>
              <th>${this.#text('history.task')}</th>
              <th>${this.#text('history.person')}</th>
              <th>${this.#text('history.chance')}</th>
              <th>${this.#text('history.status')}</th>
              <th>${this.#text('history.doneAt')}</th>
            </tr>
          </thead>
          <tbody>
            ${repeat(
              round.assignments,
              (assignment) => assignment.id,
              (assignment) => this.#tableRow(assignment, lookups),
            )}
          </tbody>
        </table>
      </div>
    `;
  }

  #tableRow(assignment: AssignmentObject, lookups: HistoryLookups): TemplateResult {
    const person = lookups.persons.get(assignment.person_id);
    return html`<tr>
      <td>${lookups.tasks.get(assignment.task_id)?.name ?? this.#text('common.unknownTask')}</td>
      <td>
        <span class="person"
          ><tw-avatar name=${person?.name ?? ''} color=${person?.color ?? ''}></tw-avatar>
          ${person?.name ?? this.#text('common.unknownPerson')}</span
        >
      </td>
      <td>${formatPercent(assignment.chance, this.language)}</td>
      <td>
        <tw-badge tone=${STATUS_TONES[assignment.status]}
          >${this.#text(`status.${assignment.status}`)}</tw-badge
        >
      </td>
      <td>
        ${
          assignment.done_at
            ? formatDateTime(assignment.done_at, this.language)
            : this.#text('common.none')
        }
      </td>
    </tr>`;
  }

  #toggle(id: string): void {
    const open = new Set(this._open);
    if (!open.delete(id)) {
      open.add(id);
    }
    this._open = open;
  }

  #query(offset: number, limit: number): { person_id?: string; offset: number; limit: number } {
    return this._filter === FILTER_ALL
      ? { offset, limit }
      : { person_id: this._filter, offset, limit };
  }

  #load(more: boolean): void {
    const client = this.#store.client;
    if (!client) {
      return;
    }
    const before = more ? this.#data.value : undefined;
    void this.#data.run(async () => {
      const page = await client.history(this.#query(before?.next ?? 0, HISTORY_PAGE_SIZE));
      return { rounds: [...(before?.rounds ?? []), ...page.entries], next: page.next_offset };
    });
  }

  #delete(roundId: string): void {
    const client = this.#store.client;
    if (!client) {
      return;
    }
    this._busy = true;
    this._deleteFailed = false;
    client
      .deleteRound(roundId)
      .then(() => {
        this.#load(false);
      })
      .catch(() => {
        this._deleteFailed = true;
      })
      .finally(() => {
        this._busy = false;
      });
  }

  #export(lookups: HistoryLookups): void {
    const client = this.#store.client;
    if (!client) {
      return;
    }
    this._exporting = true;
    this._exportFailed = false;
    this.#fetchAll(client)
      .then((rounds) => {
        const rows = csvRows(rounds, lookups, this.language, (key) => this.#text(key));
        downloadText(CSV_FILE_NAME, buildCsv(rows), CSV_MIME);
      })
      .catch(() => {
        this._exportFailed = true;
      })
      .finally(() => {
        this._exporting = false;
      });
  }

  async #fetchAll(client: ApiClient): Promise<readonly RoundObject[]> {
    const rounds: RoundObject[] = [];
    let offset: number | null = 0;
    for (let page = 0; offset !== null && page < EXPORT_MAX_PAGES; page += 1) {
      const result = await client.history(this.#query(offset, EXPORT_PAGE_SIZE));
      rounds.push(...result.entries);
      offset = result.next_offset;
    }
    return rounds;
  }
}

customElements.define(VIEW_TAGS.history, TwHistoryView);
