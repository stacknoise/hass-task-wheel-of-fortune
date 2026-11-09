import { LitElement, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';
import { createRef, ref } from 'lit/directives/ref.js';

import type { ApiClient, TaskDrawWire } from '../api/index.ts';
import '../components/index.ts';
import type { TwStage, WheelSegment } from '../components/index.ts';
import {
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
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import {
  DrawSession,
  awaitsLastSpin,
  StoreController,
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
import { drawSummary, stageNotice } from './draw-summary.ts';
import { peopleList } from './draw-people.ts';
import { ReplaceFlow } from './draw-replace.ts';
import { drawFailure, drawWindowDialog } from './draw-window.ts';
import { drawStyles } from './draw-styles.ts';
import { isCurrentTask, nameOf, taskStatus, waitingPersons, winnerOf } from './draw-rows.ts';
import { taskRow } from './task-row.ts';
import { defineOnce } from '../components/define.ts';

/** Auslosung: Zeitplan wählen, je Aufgabe das Rad drehen (Ergebnis vom Backend), Runde abschließen. */
export class TwDrawView extends LitElement {
  static override properties = {
    language: { type: String },
    _scheduleId: { state: true },
    _starting: { state: true },
  };

  static override styles = drawStyles;

  declare language: string;
  declare _scheduleId: string;
  /** Die Zeitplan-Kennung, für die der Dialog „ab wann, bis wann“ offen ist. */
  declare _starting: string;

  readonly #store = new StoreController(this);
  /** Räume des laufenden Renders. */
  #areas: AreaNames = new Map();
  readonly #stage = createRef<TwStage>();
  readonly #replace = new ReplaceFlow({
    host: this,
    session: () => this.#session,
    isAdmin: () => this.#store.client?.isAdmin() === true,
    text: (key) => this.#text(key),
    room: (task) => this.#room(task),
  });
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
    this._starting = EMPTY_TEXT;
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
      void this.#animate(current, state.results.length >= state.taskIds.length);
    }
    this.#autoSpin(state);
  }

  /** Die nächste Aufgabe der Ziehung. */
  #nextTask(state: DrawState): TaskInfo | undefined {
    const snapshot = this.#store.state?.snapshot;
    return snapshot && tasksById(snapshot).get(state.taskIds[state.results.length] ?? EMPTY_TEXT);
  }

  /**
   * Bleibt für die allerletzte Aufgabe höchstens eine Person übrig, gibt es nichts zu drehen: die
   * Ziehung läuft ohne Klick. Alle anderen Aufgaben starten nur per Klick auf „Los“. Das Backend entscheidet weiterhin (es prüft auch Pause und Abwesenheit).
   */
  #autoSpin(state: DrawState): void {
    const snapshot = this.#store.state?.snapshot;
    const task = this.#nextTask(state);
    const key = `${state.roundId ?? EMPTY_TEXT}:${String(state.results.length)}`;
    if (!snapshot || !task || !awaitsLastSpin(state) || key === this.#autoSpun) {
      return;
    }
    const taken = new Set(state.results.map((result) => result.winner_id));
    if (
      openCandidates(participantsOf(personsById(snapshot), state.participantIds), task, taken) <= 1
    ) {
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
    const persons = participantsOf(personsById(snapshot), state.participantIds);
    return html`
      <div class="layout">
        ${this.#side(state, tasks, persons)} ${this.#stagePanel(state, tasks, persons)}
      </div>
      ${this.#replace.dialog(state, tasks)}
    `;
  }

  #room(task: TaskInfo | undefined): TemplateResult | typeof nothing {
    return roomTags(this.#areas, task?.areaIds, this.#text('common.unknownArea'));
  }

  #text(key: TextKey): string {
    return translate(key, this.language);
  }

  async #animate(result: TaskDrawWire, last: boolean): Promise<void> {
    const stage = this.#stage.value;
    try {
      // Nur die allerletzte Aufgabe wird ohne Animation zugewiesen; sonst dreht das Rad immer.
      if (stage && result.winner_id && (!last || result.segments.length > 1)) {
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
        ${
          state.phase === DRAW_PHASE.error
            ? drawFailure(this.#text('draw.error'), this.#text('draw.error.code'), state.errorCode)
            : nothing
        }
      </section>
    `;
  }

  #selected(ids: readonly string[]): string {
    return ids.includes(this._scheduleId) ? this._scheduleId : (ids[0] ?? EMPTY_TEXT);
  }

  #start(scheduleId: string, open: unknown): TemplateResult {
    return html`
      <div class="actions">
        <button
          class="button primary"
          ?disabled=${!scheduleId}
          @click=${() => {
            this._starting = scheduleId;
          }}
        >
          ${this.#text('draw.start')}
        </button>
        ${open ? this.#resumeButton(scheduleId) : nothing}
      </div>
      <p class="muted">${this.#text('draw.choose')}</p>
      ${this._starting === scheduleId ? this.#windowDialog(scheduleId) : nothing}
    `;
  }

  #resumeButton(scheduleId: string): TemplateResult {
    const resume = () => {
      const snapshot = this.#store.state?.snapshot;
      const round = snapshot && openRoundFor(snapshot, scheduleId);
      if (round) {
        const kind = this.#pick(scheduleId);
        this.#session?.resume(round);
        if (kind === undefined) {
          void this.#session?.drawRest();
        }
      }
    };
    return html`<button class="button" @click=${resume}>${this.#text('draw.resume')}</button>`;
  }

  #windowDialog(scheduleId: string): TemplateResult {
    return drawWindowDialog({
      language: this.language,
      schedule: this.#schedule(scheduleId),
      now: this.#store.state?.snapshot?.now ?? EMPTY_TEXT,
      onConfirm: (request) => {
        const kind = this.#pick(scheduleId);
        this._starting = EMPTY_TEXT;
        void this.#session?.begin(
          scheduleId,
          request,
          kind !== undefined,
          this.#store.client?.isAdmin() === true,
        );
      },
      onCancel: () => {
        this._starting = EMPTY_TEXT;
      },
    });
  }

  /** Wählt zufällig eine der Animationen, die der Zeitplan erlaubt (ohne Auswahl keine), und merkt sie. */
  #pick(scheduleId: string): AnimationKind | undefined {
    const kind = pickAnimation(this.#schedule(scheduleId)?.animations ?? DEFAULT_ANIMATIONS);
    this.#kind = kind ?? this.#kind;
    return kind;
  }

  #schedule(scheduleId: string): ScheduleInfo | undefined {
    const snapshot = this.#store.state?.snapshot;
    return snapshot
      ? drawableSchedules(snapshot).find((item) => item.id === scheduleId)
      : undefined;
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
        ${
          state.phase === DRAW_PHASE.done
            ? nothing
            : html`<button
                class="button"
                ?disabled=${state.phase === DRAW_PHASE.busy}
                @click=${() => void this.#session?.restart()}
              >
                ${this.#text('draw.restart')}
              </button>`
        }
      </div>
    `;
  }

  #taskRow(
    state: DrawState,
    task: TaskInfo | undefined,
    persons: ReadonlyMap<string, PersonInfo>,
    index: number,
    shown: number,
  ): TemplateResult {
    return taskRow({
      state,
      task,
      winner: winnerOf(state, persons, index, shown),
      current: isCurrentTask(state, index, shown),
      status: taskStatus(state, index, shown, this.language),
      points: `${String(task?.points ?? 0)} ${this.#text('draw.points')}`,
      rooms: this.#room(task),
      action: task ? this.#replace.button(state, task) : nothing,
    });
  }

  // ----- Bühne: Rad, Wer ist im Rad?, Ergebnis, Abschluss -----

  #stagePanel(
    state: DrawState,
    tasks: ReadonlyMap<string, TaskInfo>,
    persons: ReadonlyMap<string, PersonInfo>,
  ): TemplateResult {
    const text = (key: TextKey): string => this.#text(key);
    const notice = stageNotice({ state, tasks, text, session: this.#session });
    if (notice) {
      return notice;
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
        ${this.#wheelBox(state, task, persons)}
        ${peopleList(this.#text('draw.who'), state, persons)}
        ${state.phase === DRAW_PHASE.revealed ? this.#result(state, task, persons) : nothing}
      </section>
    `;
  }

  /**
   * Die Segmente des Rads: alle, die noch auf eine Aufgabe warten, gleich groß (so verrät die
   * Größe nichts). Gleicher Inhalt ergibt dieselbe Liste, damit das Rad bei jedem Neuzeichnen
   * seine Drehung behält.
   */
  #wheelSegments(waiting: readonly PersonInfo[]): readonly WheelSegment[] {
    const segments = waiting.map((person) => ({
      id: person.id,
      label: person.name,
      color: person.color || FALLBACK_COLOR,
      chance: 1 / waiting.length,
    }));
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
    const segments = this.#wheelSegments(waitingPersons(state, persons));
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
