import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { modelsOf } from '../api/index.ts';
import type {
  ApiClient,
  AssignmentObject,
  HistoryPage,
  PersonObject,
  RoundHead,
  ScheduleObject,
  StatisticsReport,
  TaskObject,
} from '../api/index.ts';
import { baseStyles, tokenStyles, viewStyles } from '../components/index.ts';
import '../components/index.ts';
import {
  ACTIVITY_COUNT,
  EVENT_CHIP_SELECT,
  FILTER_ALL,
  OVERVIEW_MONTHS,
  OVERVIEW_WEEKS,
  PAIR,
  STATUS_TONES,
  VIEW_TAGS,
} from '../constants/index.ts';
import { formatDateTime, formatNumber } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey, TextParams } from '../i18n/index.ts';
import {
  AsyncValue,
  RevisionTracker,
  StoreController,
  areaNames,
  indexById,
} from '../state/index.ts';
import type { AreaNames } from '../state/index.ts';
import { roomTag } from './room.ts';
import { personChips } from './person-chips.ts';
import { assignmentGroups } from './overview-assignments.ts';
import type { AssignmentHandlers } from './overview-assignments.ts';
import { filterByPerson, groupByRound, recentActivity, upcomingDraws } from './overview-model.ts';
import { defineOnce } from '../components/define.ts';

/** Übersicht: nächste Auslosung, offene Zuteilungen mit Erledigen und Tauschen, Punkte, Aktivität. */
export class TwOverviewView extends LitElement {
  static override properties = {
    language: { type: String },
    _filter: { state: true },
    _plan: { state: true },
    _swapOpen: { state: true },
    _busy: { state: true },
    _failed: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    viewStyles,
    css`
      :host {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: var(--tw-space-m);
        align-items: stretch;
      }
      .card {
        margin: 0;
      }
      .wide {
        grid-column: 1 / -1;
      }
      .next-name {
        font-size: 1.5em;
        font-weight: 500;
      }
      ul {
        list-style: none;
        margin: 0;
        padding: 0;
      }
      li {
        padding: var(--tw-space-s) 0;
        border-top: 1px solid var(--tw-color-divider);
      }
      h3 {
        margin: 0;
        font-size: 1em;
        font-weight: 500;
      }
      .group-head {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: var(--tw-space-field);
        margin-top: var(--tw-space-field);
      }
      .group-head + ul {
        margin-top: var(--tw-space-field);
      }
      .info {
        flex-basis: 16em;
      }
      .swap {
        padding: var(--tw-space-s) 0 0 40px;
      }
      @media (min-width: 900px) {
        .assignments {
          grid-column: span 2;
        }
      }
    `,
  ];

  declare language: string;
  declare _filter: string;
  declare _plan: number;
  declare _swapOpen: string;
  declare _busy: boolean;
  declare _failed: boolean;

  readonly #store = new StoreController(this);
  readonly #points = new AsyncValue<StatisticsReport>(this);
  readonly #activity = new AsyncValue<HistoryPage>(this);
  readonly #revision = new RevisionTracker();
  #started = false;

  constructor() {
    super();
    this.language = '';
    this._filter = FILTER_ALL;
    this._plan = 0;
    this._swapOpen = '';
    this._busy = false;
    this._failed = false;
    this.addEventListener(EVENT_CHIP_SELECT, (event) => {
      this._filter = (event as CustomEvent<string>).detail;
    });
  }

  protected override willUpdate(): void {
    const client = this.#store.client;
    const changed = this.#revision.advance(this.#store.state?.snapshot);
    if (client && (!this.#started || changed)) {
      this.#started = true;
      this.#refresh(client);
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    if (!snapshot) {
      return nothing;
    }
    const persons = modelsOf(snapshot, 'persons');
    const tasks = modelsOf(snapshot, 'tasks');
    const schedules = modelsOf(snapshot, 'schedules');
    const assignments = modelsOf(snapshot, 'assignments');
    const rounds = modelsOf(snapshot, 'rounds');
    const personById = indexById(persons);
    return html`
      ${this.#nextDraw(upcomingDraws(schedules), tasks)}
      ${this.#assignments(persons, personById, indexById(tasks), schedules, assignments, rounds)}
      ${this.#pointsCard(personById)} ${this.#activityCard(personById, indexById(tasks))}
    `;
  }

  #text(key: TextKey, params?: TextParams): string {
    return translate(key, this.language, params);
  }

  #nextDraw(draws: readonly ScheduleObject[], tasks: readonly TaskObject[]): TemplateResult {
    const index = Math.min(this._plan, Math.max(draws.length - 1, 0));
    const draw = draws[index];
    return html`
      <section class="card wide" aria-live="polite">
        <h2>${this.#text('overview.next')}</h2>
        ${
          draw?.next_run
            ? this.#drawDetails(draw, draws.length, index, tasks)
            : html`<p class="empty">${this.#text('overview.nextNone')}</p>`
        }
      </section>
    `;
  }

  #drawDetails(
    draw: ScheduleObject,
    count: number,
    index: number,
    tasks: readonly TaskObject[],
  ): TemplateResult {
    const names = new Map(tasks.map((task) => [task.id, task.name]));
    const step = (delta: number): void => {
      this._plan = (index + delta + count) % count;
    };
    return html`
      <div class="row">
        <button
          type="button"
          class="action"
          aria-label=${this.#text('overview.prevPlan')}
          ?disabled=${count < PAIR}
          @click=${() => {
            step(-1);
          }}
        >
          ‹
        </button>
        <div class="grow">
          <div class="next-name">${draw.name}</div>
          <div>${formatDateTime(draw.next_run ?? '', this.language)}</div>
          <div class="muted">
            ${this.#text('overview.nextTasks', { count: draw.task_ids.length })}:
            ${draw.task_ids.map((id) => names.get(id) ?? '').join(', ')}
          </div>
          <div class="muted">
            ${this.#text('overview.position', { position: index + 1, count })}
          </div>
        </div>
        <button
          type="button"
          class="action"
          aria-label=${this.#text('overview.nextPlan')}
          ?disabled=${count < PAIR}
          @click=${() => {
            step(1);
          }}
        >
          ›
        </button>
      </div>
    `;
  }

  #assignments(
    persons: readonly PersonObject[],
    personById: ReadonlyMap<string, PersonObject>,
    taskById: ReadonlyMap<string, TaskObject>,
    schedules: readonly ScheduleObject[],
    assignments: readonly AssignmentObject[],
    rounds: readonly RoundHead[],
  ): TemplateResult {
    const visible = filterByPerson(assignments, this._filter);
    return html`
      <section class="card assignments">
        <div class="row">
          <h2 class="grow">${this.#text('overview.assignments')}</h2>
          <span class="muted"
            >${this.#text('overview.openCount', { count: assignments.length })}</span
          >
        </div>
        <tw-chips
          .items=${personChips(persons, this.#text('overview.filterAll'))}
          selected=${this._filter}
          label=${this.#text('overview.filter')}
        ></tw-chips>
        ${
          this._failed
            ? html`<p class="error" role="alert">${this.#text('overview.actionError')}</p>`
            : nothing
        }
        ${
          visible.length === 0
            ? html`<p class="empty">${this.#text('overview.noAssignments')}</p>`
            : assignmentGroups({
                language: this.language,
                groups: groupByRound(visible, rounds, schedules),
                persons,
                personById,
                taskById,
                areas: this.#areas(),
                swapOpen: this._swapOpen,
                busy: this._busy,
                handlers: this.#handlers(),
              })
        }
      </section>
    `;
  }

  #handlers(): AssignmentHandlers {
    return {
      complete: (id) => {
        this.#act((client) => client.complete(id));
      },
      deleteRound: (id) => {
        this.#act((client) => client.deleteRound(id));
      },
      skip: (id) => {
        this.#act((client) => client.skip(id));
      },
      toggleSwap: (id) => {
        this._swapOpen = this._swapOpen === id ? '' : id;
      },
      swap: (id, personId) => {
        this.#act((client) => client.swap(id, personId));
      },
    };
  }

  #pointsCard(personById: ReadonlyMap<string, PersonObject>): TemplateResult {
    const standings = [...(this.#points.value?.standings ?? [])]
      .filter((standing) => personById.has(standing.person_id))
      .sort((a, b) => b.points - a.points);
    return html`
      <section class="card">
        <h2>${this.#text('overview.pointsMonth')}</h2>
        ${this.#points.status === 'error' ? this.#loadError() : nothing}
        ${
          standings.length === 0 || standings.every((standing) => standing.points === 0)
            ? html`<p class="empty">${this.#text('overview.pointsEmpty')}</p>`
            : html`<ul>
                ${repeat(
                  standings,
                  (standing) => standing.person_id,
                  (standing) => {
                    const person = personById.get(standing.person_id);
                    return html`<li class="row nowrap">
                      <tw-avatar
                        name=${person?.name ?? ''}
                        color=${person?.color ?? ''}
                      ></tw-avatar>
                      <span class="grow">${person?.name}</span>
                      <strong class="fixed">${standing.points}</strong>
                      <span class="muted"
                        >${this.#text('overview.pointsFair', {
                          fair: formatNumber(standing.fair_points, this.language),
                        })}</span
                      >
                    </li>`;
                  },
                )}
              </ul>`
        }
      </section>
    `;
  }

  #areas(): AreaNames {
    return areaNames(this.#store.client?.areas() ?? []);
  }

  #activityCard(
    personById: ReadonlyMap<string, PersonObject>,
    taskById: ReadonlyMap<string, TaskObject>,
  ): TemplateResult {
    const items = recentActivity(this.#activity.value?.entries ?? [], ACTIVITY_COUNT);
    const areas = this.#areas();
    return html`
      <section class="card">
        <h2>${this.#text('overview.activity')}</h2>
        ${this.#activity.status === 'error' ? this.#loadError() : nothing}
        ${
          items.length === 0
            ? html`<p class="empty">${this.#text('overview.activityEmpty')}</p>`
            : html`<ul>
                ${repeat(
                  items,
                  (item) => item.assignment.id,
                  ({ assignment, at }) =>
                    html`<li class="row nowrap">
                      <span class="grow">
                        ${
                          personById.get(assignment.person_id)?.name ??
                          this.#text('common.unknownPerson')
                        }
                        ·
                        ${taskById.get(assignment.task_id)?.name ?? this.#text('common.unknownTask')}
                        ${roomTag(
                          areas,
                          taskById.get(assignment.task_id)?.area_id,
                          this.#text('common.unknownArea'),
                        )}
                        <div class="muted">${formatDateTime(at, this.language)}</div>
                      </span>
                      <tw-badge class="fixed" tone=${STATUS_TONES[assignment.status]}
                        >${this.#text(`status.${assignment.status}`)}</tw-badge
                      >
                    </li>`,
                )}
              </ul>`
        }
      </section>
    `;
  }

  #loadError(): TemplateResult {
    return html`<p class="error" role="alert">${this.#text('common.loadError')}</p>`;
  }

  #refresh(client: ApiClient): void {
    void this.#points.run(() => client.statistics(OVERVIEW_MONTHS, OVERVIEW_WEEKS));
    void this.#activity.run(() => client.history({ limit: ACTIVITY_COUNT }));
  }

  #act(task: (client: ApiClient) => Promise<unknown>): void {
    const client = this.#store.client;
    if (!client) {
      return;
    }
    this._busy = true;
    this._failed = false;
    task(client)
      .then(() => {
        this._swapOpen = '';
        this.#refresh(client);
      })
      .catch(() => {
        this._failed = true;
      })
      .finally(() => {
        this._busy = false;
      });
  }
}

defineOnce(VIEW_TAGS.overview, TwOverviewView);
