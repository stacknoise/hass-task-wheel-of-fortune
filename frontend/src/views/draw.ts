import { LitElement, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { createRef, ref } from 'lit/directives/ref.js';

import type { ApiClient, TaskDrawWire, TaskReplacementWire } from '../api/index.ts';
import '../components/index.ts';
import type { TwStage, WheelSegment } from '../components/index.ts';
import {
  CHANCE_FREE_ANIMATIONS,
  DEFAULT_ANIMATIONS,
  DRAW_PHASE,
  EMPTY_TEXT,
  EVENT_TAB_SELECT,
  FALLBACK_COLOR,
  ROUTE_HISTORY,
  START_PLACEMENT,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import { formatPercent } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import {
  DrawSession,
  StoreController,
  canReplace,
  canSkip,
  drawableSchedules,
  isIdle,
  openCandidates,
  openRoundFor,
  participantsOf,
  personsById,
  pickAnimation,
  shownCount,
  tasksById,
} from '../state/index.ts';
import type { AreaNames, DrawState, PersonInfo, ScheduleInfo, TaskInfo } from '../state/index.ts';
import { roomTags } from './room.ts';
import { drawSummary } from './draw-summary.ts';
import { drawStyles } from './draw-styles.ts';
import { personRows } from './draw-rows.ts';
import { defineOnce } from '../components/define.ts';

function nameOf(schedules: readonly ScheduleInfo[], id: string | undefined): string {
  return schedules.find((schedule) => schedule.id === id)?.name ?? EMPTY_TEXT;
}

/** Auslosung: Zeitplan wählen, je Aufgabe das Rad drehen (Ergebnis vom Backend), Runde abschließen. */
export class TwDrawView extends LitElement {
  static override properties = {
    language: { type: String },
    _scheduleId: { state: true },
    _replacing: { state: true },
    _options: { state: true },
    _pick: { state: true },
  };

  static override styles = drawStyles;

  declare language: string;
  declare _scheduleId: string;
  /** Die Aufgabe, die der Admin gerade austauscht (Dialog offen), sonst leer. */
  declare _replacing: string;
  declare _options: readonly TaskReplacementWire[];
  declare _pick: string;

  readonly #store = new StoreController(this);
  /** Räume des laufenden Renders. */
  #areas: AreaNames = new Map();
  readonly #stage = createRef<TwStage>();
  /** Die Animation der laufenden Auslosung; wird bei jedem Start zufällig neu gewählt. */
  #kind: AnimationKind = DEFAULT_ANIMATIONS[0] ?? 'wheel';
  #session: DrawSession | undefined;
  #sessionClient: ApiClient | undefined;
  #unlisten: (() => void) | undefined;
  #animating: TaskDrawWire | undefined;
  #autoSpun = EMPTY_TEXT;
  #wheelCache: { key: string; segments: readonly WheelSegment[] } | undefined;

  constructor() {
    super();
    this.language = EMPTY_TEXT;
    this._scheduleId = EMPTY_TEXT;
    this._replacing = EMPTY_TEXT;
    this._options = [];
    this._pick = EMPTY_TEXT;
  }

  /**
   * Die Sitzung überlebt einen Tabwechsel (das Panel hängt die Ansicht nur aus); eine laufende
   * Animation wird beim Zurückkehren neu gestartet, ihr Ergebnis steht ja schon fest.
   */
  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this.#animating = undefined;
  }

  protected override willUpdate(): void {
    const client = this.#store.client;
    if (client && client !== this.#sessionClient) {
      this.#sessionClient = client;
      this.#unlisten?.();
      this.#session = new DrawSession(client);
      this.#unlisten = this.#session.listen(() => {
        this.requestUpdate();
      });
    }
  }

  protected override updated(): void {
    const state = this.#session?.state;
    if (!state) {
      return;
    }
    const current = state.phase === DRAW_PHASE.spinning ? state.current : undefined;
    if (current && current !== this.#animating) {
      this.#animating = current;
      void this.#animate(current);
    }
    this.#autoSpin(state);
  }

  /** Die Aufgabe, die als Nächstes gezogen wird. */
  #nextTask(state: DrawState): TaskInfo | undefined {
    const snapshot = this.#store.state?.snapshot;
    const taskId = state.taskIds[state.results.length];
    return snapshot && taskId ? tasksById(snapshot).get(taskId) : undefined;
  }

  /**
   * Bleibt für die nächste Aufgabe höchstens eine Person übrig, gibt es nichts zu drehen: die
   * Ziehung läuft ohne Klick, das Backend entscheidet weiterhin (es prüft auch Pause und Abwesenheit).
   */
  #autoSpin(state: DrawState): void {
    const snapshot = this.#store.state?.snapshot;
    const task = this.#nextTask(state);
    const key = `${state.roundId ?? EMPTY_TEXT}:${String(state.results.length)}`;
    if (!snapshot || state.phase !== DRAW_PHASE.ready || !task || key === this.#autoSpun) {
      return;
    }
    const taken = new Set(state.results.map((result) => result.winner_id));
    if (openCandidates(personsById(snapshot), task, taken) <= 1) {
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
    this.#areas = this.#store.areaNames();
    const state = session.state;
    const tasks = tasksById(snapshot);
    const persons = participantsOf(personsById(snapshot), tasks, state.taskIds);
    return html`
      <div class="layout">
        ${this.#side(state, tasks, persons)} ${this.#stagePanel(state, tasks, persons)}
      </div>
      ${this._replacing && canReplace(state) ? this.#replaceDialog(tasks) : nothing}
    `;
  }

  #room(task: TaskInfo | undefined): TemplateResult | typeof nothing {
    return roomTags(this.#areas, task?.areaIds, this.#text('common.unknownArea'));
  }

  #text(key: TextKey): string {
    return translate(key, this.language);
  }

  async #animate(result: TaskDrawWire): Promise<void> {
    const stage = this.#stage.value;
    try {
      if (stage && result.winner_id && result.segments.length > 1) {
        await stage.updateComplete;
        await stage.spinTo(result.winner_id);
      }
    } finally {
      // Ohne Dokument (Tabwechsel) bleibt die Phase stehen; die Animation startet beim Zurückkehren neu.
      if (this.isConnected) {
        this.#session?.landed();
      }
    }
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
    const idle = isIdle(state);
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
        ${
          idle
            ? this.#start(scheduleId, open)
            : this.#round(state, nameOf(schedules, state.scheduleId), tasks, persons)
        }
        ${state.phase === DRAW_PHASE.error ? this.#failure(state) : nothing}
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
          @click=${() => {
            const kind = this.#pick(scheduleId);
            this.#kind = kind ?? this.#kind;
            void session?.begin(scheduleId, kind !== undefined);
          }}
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
                    const kind = this.#pick(scheduleId);
                    this.#kind = kind ?? this.#kind;
                    session?.resume(round);
                    if (kind === undefined) {
                      void session?.drawRest();
                    }
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

  /** Wählt zufällig eine der Animationen, die der Zeitplan erlaubt; ohne Auswahl keine. */
  #pick(scheduleId: string): AnimationKind | undefined {
    const snapshot = this.#store.state?.snapshot;
    const schedule = snapshot
      ? drawableSchedules(snapshot).find((candidate) => candidate.id === scheduleId)
      : undefined;
    return pickAnimation(schedule?.animations ?? DEFAULT_ANIMATIONS);
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
    const shown = shownCount(state);
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
          canSkip(state)
            ? html`<button class="button" @click=${() => void this.#session?.drawRest()}>
                ${this.#text('draw.rest')}
              </button>`
            : nothing
        }
        <button
          class="button"
          ?disabled=${state.phase === DRAW_PHASE.busy}
          @click=${() => void this.#session?.restart()}
        >
          ${this.#text('draw.restart')}
        </button>
      </div>
    `;
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
    return index === shown && state.phase !== DRAW_PHASE.done;
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
          ${this.#room(task)}
        </span>
        <span class="status">${this.#taskStatus(state, persons, index, shown)}</span>
        ${task && this.#canReplace(state) ? this.#replaceButton(task) : nothing}
      </li>
    `;
  }

  // ----- Aufgabe vor dem Start austauschen (nur Administratoren) -----

  #canReplace(state: DrawState): boolean {
    return canReplace(state) && this.#store.client?.isAdmin() === true;
  }

  #replaceButton(task: TaskInfo): TemplateResult {
    return html`<button
      class="button"
      aria-label="${this.#text('draw.replace')}: ${task.name}"
      @click=${() => void this.#openReplace(task.id)}
    >
      ${this.#text('draw.replace')}
    </button>`;
  }

  async #openReplace(taskId: string): Promise<void> {
    this._options = (await this.#session?.replacements()) ?? [];
    this._pick = this._options.find((option) => option.doable)?.task_id ?? EMPTY_TEXT;
    this._replacing = taskId;
  }

  #closeReplace(): void {
    this._replacing = EMPTY_TEXT;
  }

  #replaceDialog(tasks: ReadonlyMap<string, TaskInfo>): TemplateResult {
    return html`
      <tw-dialog
        language=${this.language}
        label=${this.#text('draw.replace.title')}
        @tw-cancel=${() => {
          this.#closeReplace();
        }}
      >
        <p>
          <strong>${this.#text('draw.replace.out')}</strong>
          ${tasks.get(this._replacing)?.name ?? EMPTY_TEXT}
        </p>
        <fieldset class="options">
          <legend class="muted">${this.#text('draw.replace.with')}</legend>
          ${
            this._options.length === 0
              ? html`<span class="muted">${this.#text('draw.replace.none')}</span>`
              : this._options.map((option) => this.#replaceOption(option, tasks))
          }
        </fieldset>
        <p class="muted">${this.#text('draw.replace.hint')}</p>
        <div class="actions" slot="actions">
          <button
            class="button primary"
            ?disabled=${!this._pick}
            @click=${() => {
              const from = this._replacing;
              this.#closeReplace();
              void this.#session?.replaceTask(from, this._pick);
            }}
          >
            ${this.#text('draw.replace.apply')}
          </button>
          <button
            class="button"
            @click=${() => {
              this.#closeReplace();
            }}
          >
            ${this.#text('form.cancel')}
          </button>
        </div>
      </tw-dialog>
    `;
  }

  #replaceOption(
    option: TaskReplacementWire,
    tasks: ReadonlyMap<string, TaskInfo>,
  ): TemplateResult {
    return html`
      <label class="option ${option.doable ? '' : 'out'}">
        <input
          type="radio"
          name="replacement"
          .value=${option.task_id}
          ?disabled=${!option.doable}
          .checked=${option.doable && this._pick === option.task_id}
          @change=${() => {
            this._pick = option.task_id;
          }}
        />
        <span>
          <strong>${tasks.get(option.task_id)?.name ?? option.task_id}</strong><br />
          <span class="muted"
            >${this.#text(option.doable ? 'draw.replace.doable' : 'draw.replace.infeasible')}</span
          >
        </span>
      </label>
    `;
  }

  // ----- Bühne: Rad, Wer ist im Rad?, Ergebnis, Abschluss -----

  #stagePanel(
    state: DrawState,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    if (isIdle(state)) {
      return html`<section class="stage idle">
        <p class="heading">${this.#text('draw.choose')}</p>
      </section>`;
    }
    if (state.phase === DRAW_PHASE.done) {
      return html`<section class="stage">
        ${drawSummary({
          state,
          tasks,
          persons,
          text: (key) => this.#text(key),
          room: (task) => this.#room(task),
          onHistory: () => {
            this.#toHistory();
          },
          onAgain: () => void this.#session?.restart(),
        })}
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
          ${this.#room(task)}
        </div>
        ${this.#wheelBox(state, task, persons)} ${this.#people(state, task, persons)}
        ${state.phase === DRAW_PHASE.revealed ? this.#result(state, task, persons) : nothing}
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

  #wheelBox(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const segments = this.#wheelSegments(state.current ?? state.preview, persons);
    return html`
      <div class="wheel-box ${START_PLACEMENT[this.#kind]}">
        <tw-stage
          ${ref(this.#stage)}
          .kind=${this.#kind}
          .segments=${segments}
          .label=${this.#text(`animation.${this.#kind}` as TextKey)}
          .taskName=${task?.name ?? EMPTY_TEXT}
          .language=${this.language}
          @tw-stage-start=${() => void this.#session?.spin()}
        ></tw-stage>
        <button
          class="hub ${START_PLACEMENT[this.#kind]}"
          aria-label=${this.#text('draw.spin.label')}
          ?disabled=${state.phase !== DRAW_PHASE.ready}
          @click=${() => void this.#session?.spin()}
        >
          ${this.#text(state.phase === DRAW_PHASE.busy ? 'draw.busy' : 'draw.spin')}
        </button>
      </div>
    `;
  }

  #people(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const showChance = !CHANCE_FREE_ANIMATIONS.includes(this.#kind);
    const rows = personRows(
      state.current ?? state.preview,
      task,
      persons,
      showChance,
      this.language,
    );
    return html`
      <div class="people">
        <span class="eyebrow">${this.#text('draw.who')}</span>
        ${repeat(
          rows,
          (row) => row.person.id,
          (row) => html`
            <div class="person ${row.inWheel ? '' : 'out'}">
              <tw-avatar name=${row.person.name} color=${row.person.color}></tw-avatar>
              <div>${row.person.name}<br /><span class="muted">${row.note}</span></div>
            </div>
          `,
        )}
        ${showChance ? html`<span class="muted hint">${this.#text('draw.who.hint')}</span>` : nothing}
      </div>
    `;
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
            ? html`<tw-avatar name=${winner.name} color=${winner.color}></tw-avatar>
                <div class="text">
                  <strong>${winner.name} ${this.#text('draw.takes')} ${task?.name}</strong><br />
                  ${this.#room(task)}
                  <span class="muted"
                    >${this.#text('draw.chance')}
                    ${formatPercent(state.current?.chance ?? 0, this.language)}</span
                  >
                </div>`
            : html`<div class="text">
                <strong>${this.#text('draw.nobody')} ${task?.name}</strong><br />
                ${this.#room(task)}
                <span class="muted">${this.#text('draw.nobody.hint')}</span>
              </div>`
        }
        <button class="button primary" @click=${() => void this.#session?.next()}>
          ${this.#text(last ? 'draw.finish' : 'draw.next')}
        </button>
      </div>
    `;
  }

  #toHistory(): void {
    this.dispatchEvent(
      new CustomEvent(EVENT_TAB_SELECT, { detail: ROUTE_HISTORY, bubbles: true, composed: true }),
    );
  }
}

defineOnce(VIEW_TAGS.draw, TwDrawView);
