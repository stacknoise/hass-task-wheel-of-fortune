import { LitElement, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { createRef, ref } from 'lit/directives/ref.js';

import type { TaskDrawWire } from '../api/index.ts';
import { percentText } from '../components/index.ts';
import '../components/index.ts';
import type { TwWheel, WheelSegment } from '../components/index.ts';
import { EMPTY_TEXT, EVENT_TAB_SELECT, FALLBACK_COLOR, VIEW_TAGS } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import {
  DrawSession,
  StoreController,
  drawableSchedules,
  openRoundFor,
  personsById,
  tasksById,
} from '../state/index.ts';
import type { DrawState, PersonInfo, ScheduleInfo, TaskInfo } from '../state/index.ts';

import { drawStyles } from './draw-styles.ts';

const HISTORY_ROUTE = 'history';
const NOT_ALLOWED = 'not_allowed';

function nameOf(schedules: readonly ScheduleInfo[], id: string | undefined): string {
  return schedules.find((schedule) => schedule.id === id)?.name ?? EMPTY_TEXT;
}

interface Row {
  readonly person: PersonInfo;
  readonly note: string;
  readonly inWheel: boolean;
}

/** Auslosung: Zeitplan wählen, je Aufgabe das Rad drehen (Ergebnis vom Backend), Runde abschließen. */
export class TwDrawView extends LitElement {
  static override properties = {
    language: { type: String },
    _scheduleId: { state: true },
  };

  static override styles = drawStyles;

  declare language: string;
  declare _scheduleId: string;

  readonly #store = new StoreController(this);
  readonly #wheel = createRef<TwWheel>();
  #session: DrawSession | undefined;
  #animating: TaskDrawWire | undefined;
  #autoSpun = EMPTY_TEXT;
  #wheelCache: { key: string; segments: readonly WheelSegment[] } | undefined;

  constructor() {
    super();
    this.language = EMPTY_TEXT;
    this._scheduleId = EMPTY_TEXT;
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.#session = undefined;
  }

  protected override willUpdate(): void {
    const client = this.#store.client;
    if (!this.#session && client) {
      this.#session = new DrawSession(client);
      this.#session.listen(() => {
        this.requestUpdate();
      });
    }
  }

  protected override updated(): void {
    const state = this.#session?.state;
    if (!state) {
      return;
    }
    const current = state.phase === 'spinning' ? state.current : undefined;
    if (current && current !== this.#animating) {
      this.#animating = current;
      void this.#animate(current);
    }
    this.#autoSpin(state);
  }

  /**
   * Bleibt für die nächste Aufgabe höchstens eine Person übrig, gibt es nichts zu drehen: die
   * Ziehung läuft ohne Klick, das Backend entscheidet weiterhin (es prüft auch Pause und Abwesenheit).
   */
  #autoSpin(state: DrawState): void {
    const snapshot = this.#store.state?.snapshot;
    const taskId = state.taskIds[state.results.length];
    const task = snapshot && taskId ? tasksById(snapshot).get(taskId) : undefined;
    const key = `${state.roundId ?? EMPTY_TEXT}:${String(state.results.length)}`;
    if (state.phase !== 'ready' || !task || key === this.#autoSpun) {
      return;
    }
    const taken = new Set(state.results.map((result) => result.winner_id));
    if ([...task.allowed].filter((id) => !taken.has(id)).length <= 1) {
      this.#autoSpun = key;
      void this.#session?.spin();
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.#store.state?.snapshot;
    const session = this.#session;
    if (!snapshot || !session) {
      return nothing;
    }
    const state = session.state;
    const persons = personsById(snapshot);
    const tasks = tasksById(snapshot);
    return html`
      <div class="layout">
        ${this.#side(state, tasks, persons)} ${this.#stage(state, tasks, persons)}
      </div>
    `;
  }

  #text(key: TextKey): string {
    return translate(key, this.language);
  }

  #idle(state: DrawState): boolean {
    return state.phase === 'choose' || state.phase === 'error';
  }

  async #animate(result: TaskDrawWire): Promise<void> {
    const wheel = this.#wheel.value;
    if (wheel && result.winner_id && result.segments.length > 1) {
      await wheel.updateComplete;
      await wheel.spinTo(result.winner_id);
    }
    this.#session?.landed();
  }

  // ----- linke Karte: Zeitplan, Runde, Aufgabenliste -----

  #side(
    state: DrawState,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const snapshot = this.#store.state?.snapshot;
    const schedules = snapshot ? drawableSchedules(snapshot) : [];
    const scheduleId = this.#selected(schedules.map((schedule) => schedule.id));
    const open = snapshot && scheduleId ? openRoundFor(snapshot, scheduleId) : undefined;
    const idle = this.#idle(state);
    return html`
      <section class="card">
        <div>
          <label for="schedule">${this.#text('draw.schedule')}</label>
          <select
            id="schedule"
            .value=${scheduleId}
            ?disabled=${!idle}
            @change=${(event: Event) => {
              this._scheduleId = (event.target as HTMLSelectElement).value;
            }}
          >
            ${repeat(
              schedules,
              (schedule) => schedule.id,
              (schedule) => html`<option value=${schedule.id}>${schedule.name}</option>`,
            )}
          </select>
          ${
            schedules.length === 0
              ? html`<span class="muted">${this.#text('draw.schedule.none')}</span>`
              : nothing
          }
        </div>
        ${idle ? this.#start(scheduleId, open) : this.#round(state, nameOf(schedules, state.scheduleId), tasks, persons)}
        ${state.phase === 'error' ? this.#failure(state) : nothing}
      </section>
    `;
  }

  #selected(ids: readonly string[]): string {
    return ids.includes(this._scheduleId) ? this._scheduleId : (ids[0] ?? EMPTY_TEXT);
  }

  #start(scheduleId: string, open: unknown): TemplateResult {
    const session = this.#session;
    return html`
      <div class="actions">
        <button
          class="button primary"
          ?disabled=${!scheduleId}
          @click=${() => void session?.begin(scheduleId)}
        >
          ${this.#text('draw.start')}
        </button>
        ${
          open
            ? html`<button
                class="button"
                @click=${() => {
                  const snapshot = this.#store.state?.snapshot;
                  const round = snapshot && openRoundFor(snapshot, scheduleId);
                  if (round) {
                    session?.resume(round);
                  }
                }}
              >
                ${this.#text('draw.resume')}
              </button>`
            : nothing
        }
      </div>
      <p class="muted">${this.#text('draw.choose')}</p>
    `;
  }

  #failure(state: DrawState): TemplateResult {
    return html`<p class="error" role="alert">
      ${this.#text('draw.error')} (${this.#text('draw.error.code')}: ${state.errorCode})
    </p>`;
  }

  #round(
    state: DrawState,
    scheduleName: string,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const shown = this.#shownCount(state);
    const canSkip =
      (state.phase === 'ready' || state.phase === 'revealed') && shown < state.taskIds.length;
    return html`
      <div>
        <h2>${this.#text('draw.round')} „${scheduleName}“</h2>
        <span class="muted">${shown} / ${state.taskIds.length} ${this.#text('draw.drawn')}</span>
      </div>
      <ul>
        ${state.taskIds.map((taskId, index) =>
          this.#taskRow(state, tasks.get(taskId), persons, index, shown),
        )}
      </ul>
      <div class="actions">
        ${
          canSkip
            ? html`<button class="button" @click=${() => void this.#session?.drawRest()}>
                ${this.#text('draw.rest')}
              </button>`
            : nothing
        }
        <button class="button" @click=${() => void this.#session?.restart()}>
          ${this.#text('draw.restart')}
        </button>
      </div>
    `;
  }

  /** Wie viele Ergebnisse schon gezeigt werden dürfen: das gerade drehende bleibt verborgen. */
  #shownCount(state: DrawState): number {
    return state.phase === 'spinning' ? state.results.length - 1 : state.results.length;
  }

  /** Was in der Aufgabenliste rechts steht: der Gewinner, „nicht verteilbar“, „ist dran“ oder „wartet“. */
  #taskStatus(
    state: DrawState,
    persons: ReadonlyMap<string, PersonInfo>,
    index: number,
    shown: number,
  ): string {
    if (index < shown) {
      const winner = persons.get(state.results[index]?.winner_id ?? EMPTY_TEXT);
      return winner?.name ?? this.#text('draw.undistributable');
    }
    return this.#text(this.#isCurrent(state, index, shown) ? 'draw.current' : 'draw.waiting');
  }

  #isCurrent(state: DrawState, index: number, shown: number): boolean {
    return index === shown && state.phase !== 'done';
  }

  #taskRow(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
    index: number,
    shown: number,
  ): TemplateResult {
    return html`
      <li class="task ${this.#isCurrent(state, index, shown) ? 'current' : ''}">
        <span>
          ${task?.name ?? EMPTY_TEXT}<br />
          <span class="muted"
            >${task?.points ?? 0} ${this.#text('draw.points')} · ${task?.dueDays ?? 0}
            ${this.#text('draw.due')}</span
          >
        </span>
        <span class="status">${this.#taskStatus(state, persons, index, shown)}</span>
      </li>
    `;
  }

  // ----- Bühne: Rad, Wer ist im Rad?, Ergebnis, Abschluss -----

  #stage(
    state: DrawState,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    if (this.#idle(state)) {
      return html`<section class="stage">
        <p class="heading">${this.#text('draw.choose')}</p>
      </section>`;
    }
    const taskId = state.current?.task_id ?? state.taskIds[state.results.length];
    const task = taskId ? tasks.get(taskId) : undefined;
    const step = Math.min(state.results.length + (state.current ? 0 : 1), state.taskIds.length);
    return html`
      <section class="stage">
        <div class="heading">
          <span class="eyebrow">${this.#text('draw.step')} ${step} / ${state.taskIds.length}</span>
          <span class="title">${task?.name ?? EMPTY_TEXT}</span>
        </div>
        ${this.#wheelBox(state, persons)} ${this.#people(state, task, persons)}
        ${state.phase === 'revealed' ? this.#result(state, task, persons) : nothing}
        ${state.phase === 'done' ? this.#summary(state, tasks, persons) : nothing}
      </section>
    `;
  }

  /**
   * Die Segmente des Rads: vor dem Drehen aus der Vorschau, danach aus dem Ergebnis. Gleicher
   * Inhalt ergibt dieselbe Liste, damit das Rad bei jedem Neuzeichnen seine Drehung behält.
   */
  #wheelSegments(
    result: TaskDrawWire | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): readonly WheelSegment[] {
    const segments = (result?.segments ?? []).map((segment) => {
      const person = persons.get(segment.person_id);
      return {
        id: segment.person_id,
        label: person?.name ?? segment.person_id,
        color: person?.color ?? FALLBACK_COLOR,
        chance: segment.chance,
      };
    });
    const key = JSON.stringify(segments);
    if (this.#wheelCache?.key !== key) {
      this.#wheelCache = { key, segments };
    }
    return this.#wheelCache.segments;
  }

  #wheelBox(state: DrawState, persons: ReadonlyMap<string, PersonInfo>): TemplateResult {
    const segments = this.#wheelSegments(state.current ?? state.preview, persons);
    return html`
      <div class="wheel-box">
        <tw-wheel
          ${ref(this.#wheel)}
          .segments=${segments}
          .label=${this.#text('draw.wheel')}
        ></tw-wheel>
        <button
          class="hub"
          aria-label=${this.#text('draw.spin.label')}
          ?disabled=${state.phase !== 'ready'}
          @click=${() => void this.#session?.spin()}
        >
          ${this.#text(state.phase === 'busy' ? 'draw.busy' : 'draw.spin')}
        </button>
      </div>
    `;
  }

  #people(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const rows = this.#rows(state.current ?? state.preview, task, persons);
    return html`
      <div class="people">
        <span class="eyebrow">${this.#text('draw.who')}</span>
        ${repeat(
          rows,
          (row) => row.person.id,
          (row) => html`
            <div class="person ${row.inWheel ? '' : 'out'}">
              <div class="avatar" style="background:${row.person.color}">
                ${row.person.name.slice(0, 1)}
              </div>
              <div>${row.person.name}<br /><span class="muted">${row.note}</span></div>
            </div>
          `,
        )}
        <span class="muted hint">${this.#text('draw.who.hint')}</span>
      </div>
    `;
  }

  /** Jede Person mit ihrer Chance oder dem Grund, warum sie nicht im Rad ist. */
  #rows(
    result: TaskDrawWire | undefined,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): readonly Row[] {
    const chances = new Map(result?.segments.map((segment) => [segment.person_id, segment.chance]));
    const reasons = new Map(result?.exclusions.map((item) => [item.person_id, item.reason]));
    return [...persons.values()].map((person) => {
      const chance = chances.get(person.id);
      if (chance !== undefined) {
        return { person, inWheel: true, note: percentText(chance) };
      }
      const allowed = task?.allowed.has(person.id) ?? false;
      const reason = allowed ? reasons.get(person.id) : NOT_ALLOWED;
      return {
        person,
        inWheel: !result && allowed,
        note: reason ? this.#text(`draw.reason.${reason}` as TextKey) : EMPTY_TEXT,
      };
    });
  }

  #result(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const winner = persons.get(state.current?.winner_id ?? EMPTY_TEXT);
    const last = state.results.length >= state.taskIds.length;
    return html`
      ${winner ? html`<tw-confetti></tw-confetti>` : nothing}
      <div class="result" role="status">
        ${
          winner
            ? html`<div class="avatar" style="background:${winner.color}">
                  ${winner.name.slice(0, 1)}
                </div>
                <div class="text">
                  <strong>${winner.name} ${this.#text('draw.takes')} ${task?.name}</strong><br />
                  <span class="muted"
                    >${this.#text('draw.chance')} ${percentText(state.current?.chance ?? 0)}</span
                  >
                </div>`
            : html`<div class="text">
                <strong>${this.#text('draw.nobody')} ${task?.name}</strong><br />
                <span class="muted">${this.#text('draw.nobody.hint')}</span>
              </div>`
        }
        <button class="button primary" @click=${() => void this.#session?.next()}>
          ${this.#text(last ? 'draw.finish' : 'draw.next')}
        </button>
      </div>
    `;
  }

  #summary(
    state: DrawState,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    return html`
      <tw-confetti></tw-confetti>
      <div class="done" role="status">
        <span class="eyebrow">${this.#text('draw.done.title')}</span>
        <span class="title"
          >${this.#text(state.results.length > 0 ? 'draw.done.all' : 'draw.done.none')}</span
        >
        <ul class="summary">
          ${state.results.map(
            (result) => html`
              <li>
                <span>${tasks.get(result.task_id)?.name ?? result.task_id}</span>
                <strong
                  >${
                    persons.get(result.winner_id ?? EMPTY_TEXT)?.name ??
                    this.#text('draw.undistributable')
                  }</strong
                >
              </li>
            `,
          )}
        </ul>
        <div class="actions">
          <button
            class="button"
            @click=${() => {
              this.dispatchEvent(
                new CustomEvent(EVENT_TAB_SELECT, {
                  detail: HISTORY_ROUTE,
                  bubbles: true,
                  composed: true,
                }),
              );
            }}
          >
            ${this.#text('draw.done.history')}
          </button>
          <button class="button" @click=${() => void this.#session?.restart()}>
            ${this.#text('draw.done.again')}
          </button>
        </div>
      </div>
    `;
  }
}

customElements.define(VIEW_TAGS.draw, TwDrawView);
