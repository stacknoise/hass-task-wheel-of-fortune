import { LitElement, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { modelsOf } from '../api/index.ts';
import type { DecisionRecord, DecisionTask, PersonObject } from '../api/index.ts';
import { baseStyles, tokenStyles, viewStyles } from '../components/index.ts';
import type { ChipItem, SelectOption } from '../components/index.ts';
import { onChange } from '../components/change.ts';
import { defineOnce } from '../components/define.ts';
import '../components/index.ts';
import {
  DECISION_KINDS,
  DECISION_OUTCOMES,
  DECISION_PAGE_SIZE,
  DECISION_PAGE_SIZE_MAX,
  FILTER_ALL,
  SETTING_DECISION_RETENTION,
  VIEW_TAGS,
} from '../constants/index.ts';
import { formatDateTime } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';
import { PagedList, StoreController, indexById } from '../state/index.ts';
import { listPlaceholder, loadMore } from './load-more.ts';
import { originText } from './history-model.ts';
import {
  candidateLines,
  counts,
  exchangeText,
  showsRecord,
  tasksMatching,
  winnerName,
} from './decisions-model.ts';
import { decisionStyles } from './decisions-styles.ts';

/** Entscheidungslog: je Auslosung und Aufgabe, wer im Rad war, wer warum nicht und wie die Wahl fiel. */
export class TwDecisionsView extends LitElement {
  static override properties = {
    language: { type: String },
    _outcome: { state: true },
    _schedule: { state: true },
    _person: { state: true },
  };

  static override styles = [tokenStyles, baseStyles, viewStyles, decisionStyles];

  declare language: string;
  declare _outcome: string;
  declare _schedule: string;
  declare _person: string;

  readonly #store = new StoreController(this);
  readonly #list = new PagedList<DecisionRecord>(
    this,
    this.#store,
    (client, offset, limit) => client.decisions(this.#query(offset, limit)),
    DECISION_PAGE_SIZE,
    DECISION_PAGE_SIZE_MAX,
  );

  constructor() {
    super();
    this.language = '';
    this._outcome = FILTER_ALL;
    this._schedule = FILTER_ALL;
    this._person = FILTER_ALL;
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    if (!snapshot) {
      return nothing;
    }
    const persons = modelsOf(snapshot, 'persons');
    const days = snapshot.settings[SETTING_DECISION_RETENTION];
    return html`
      <div class="row card head">
        <h2 class="grow">${this.#text('log.title')}</h2>
        ${typeof days === 'number' ? html`<tw-badge tone="neutral">${this.#text('log.retention', { days })}</tw-badge>` : nothing}
        <p class="muted full">${this.#text('log.retentionHint')}</p>
      </div>
      ${this.#filters(
        persons,
        modelsOf(snapshot, 'schedules').map((s) => ({ id: s.id, label: s.name })),
      )}
      ${this.#body(indexById(persons))}
    `;
  }

  protected override willUpdate(): void {
    this.#list.sync();
  }

  #text(key: TextKey, params?: TextParams): string {
    return translate(key, this.language, params);
  }

  #filters(persons: readonly PersonObject[], schedules: readonly SelectOption[]): TemplateResult {
    const outcomes: readonly ChipItem[] = [
      { id: FILTER_ALL, label: this.#text('overview.filterAll') },
      { id: DECISION_OUTCOMES.assigned, label: this.#text('log.filter.assigned') },
      { id: DECISION_OUTCOMES.unassigned, label: this.#text('log.filter.unassigned') },
    ];
    const all = (key: TextKey): SelectOption => ({ id: FILTER_ALL, label: this.#text(key) });
    return html`
      <div class="card filters">
        <tw-chips
          @tw-chip-select=${(event: Event) => {
            this._outcome = (event as CustomEvent<string>).detail;
          }}
          .items=${outcomes}
          selected=${this._outcome}
          label=${this.#text('log.filterOutcome')}
        ></tw-chips>
        <div class="row">
          <tw-select
            class="grow"
            label=${this.#text('log.schedule')}
            .options=${[all('log.allSchedules'), ...schedules]}
            value=${this._schedule}
            @tw-change=${onChange<string>((value) => {
              this._schedule = value;
              this.#list.reload();
            })}
          ></tw-select>
          <tw-select
            class="grow"
            label=${this.#text('log.person')}
            .options=${[all('log.allPersons'), ...persons.map((p) => ({ id: p.id, label: p.name }))]}
            value=${this._person}
            @tw-change=${onChange<string>((value) => {
              this._person = value;
              this.#list.reload();
            })}
          ></tw-select>
        </div>
      </div>
    `;
  }

  #body(persons: ReadonlyMap<string, PersonObject>): TemplateResult {
    const list = this.#list;
    const waiting = listPlaceholder(list, (key) => this.#text(key));
    if (waiting) {
      return waiting;
    }
    const items = list.items ?? [];
    const shown = items.filter((record) => showsRecord(record, this._outcome));
    const more = loadMore(this.#text('log.more'), list.hasMore, list.status, () => {
      list.more();
    });
    if (shown.length === 0) {
      const key = items.length === 0 ? 'log.empty' : 'log.emptyFilter';
      return html`<p class="empty">${this.#text(key)}</p>
        ${more}`;
    }
    return html`
      ${repeat(
        shown,
        (record) => record.id,
        (record) => this.#record(record, persons),
      )}
      ${more}
    `;
  }

  #record(record: DecisionRecord, persons: ReadonlyMap<string, PersonObject>): TemplateResult {
    const exchange = record.exchange;
    const tally = counts(record);
    const origin =
      record.origin === null ? '' : ` · ${originText(record.origin, (key) => this.#text(key))}`;
    return html`
      <details class="card record">
        <summary>
          <span class="grow titles">
            <strong>${record.schedule_name}</strong>
            <span class="muted">${formatDateTime(record.at, this.language)}${origin}</span>
          </span>
          ${
            exchange
              ? html`<tw-badge tone="info"
                  >${this.#text(record.kind === DECISION_KINDS.swap ? 'log.kind.swap' : 'log.kind.exchange')}</tw-badge
                >`
              : html`<tw-badge tone="success"
                    >${this.#text('log.summary.assigned', { count: tally.assigned })}</tw-badge
                  >
                  ${tally.unassigned > 0 ? html`<tw-badge tone="error">${this.#text('log.summary.unassigned', { count: tally.unassigned })}</tw-badge>` : nothing}`
          }
          <span class="chevron" aria-hidden="true">▾</span>
        </summary>
        ${
          exchange
            ? html`<p class="why">
                ${exchangeText(exchange, (key, params) => this.#text(key, params))}
                <tw-badge tone="neutral"
                  >${this.#text(exchange.before_start ? 'log.beforeStart' : 'log.afterStart')}</tw-badge
                >
              </p>`
            : repeat(
                tasksMatching(record, this._outcome),
                (task) => task.task_id,
                (task) => this.#task(task, persons),
              )
        }
      </details>
    `;
  }

  #task(task: DecisionTask, persons: ReadonlyMap<string, PersonObject>): TemplateResult {
    const winner = winnerName(task);
    const heading =
      winner === undefined
        ? this.#text('log.taskUnassigned', { task: task.task_name })
        : this.#text('log.taskAssigned', { task: task.task_name, person: winner });
    return html`
      <details class="task">
        <summary>
          <strong class="grow">${heading}</strong>
          <span class="chevron" aria-hidden="true">▾</span>
        </summary>
        ${candidateLines(task, this.language, (key, params) => this.#text(key, params)).map(
          (line) =>
            html`<div class="cand">
              <span class="who">
                <tw-avatar
                  name=${line.name}
                  color=${persons.get(line.personId)?.color ?? ''}
                ></tw-avatar>
                <strong>${line.name}</strong>
              </span>
              <span
                ><tw-badge tone=${line.tone}>${line.pill}</tw-badge>
                <span class="why">${line.detail}</span></span
              >
            </div>`,
        )}
        ${winner === undefined ? html`<p class="why">${this.#text('log.unassignedResult')}</p>` : nothing}
      </details>
    `;
  }

  #query(
    offset: number,
    limit: number,
  ): { schedule_id?: string; person_id?: string; offset: number; limit: number } {
    return {
      ...(this._schedule === FILTER_ALL ? {} : { schedule_id: this._schedule }),
      ...(this._person === FILTER_ALL ? {} : { person_id: this._person }),
      offset,
      limit,
    };
  }
}

defineOnce(VIEW_TAGS.decisions, TwDecisionsView);
