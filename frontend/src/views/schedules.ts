import { css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import type { ScheduleWire, Snapshot } from '../api/index.ts';
import { describeInterval, onChange } from '../components/index.ts';
import type { ChipOption } from '../components/index.ts';
import type { AnimationKind, IntervalUnit, ScheduleMode } from '../constants/index.ts';
import { formatDateTime } from '../i18n/format.ts';
import { translate } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import '../components/index.ts';
import {
  ANIMATION_KINDS,
  DEFAULT_ANIMATIONS,
  DEFAULT_RUN_DAYS,
  EVENT_DRAWN_NAME,
  FORM_LIMITS,
  INTERVAL_UNITS,
  SCHEDULE_MODES,
  SERVICE_DRAW,
  VIEW_TAGS,
} from '../constants/index.ts';
import {
  INTERVAL_DEFAULT,
  PlanPreviewLoader,
  animationsOf,
  defaultStart,
  fromLocalInput,
  localInput,
} from '../state/index.ts';
import type { EntryWire, IntervalWire } from '../state/index.ts';
import { personOptions, taskOptions } from './chip-options.ts';
import { ConfigView } from './config-view.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

/** Formularstand: wie `ScheduleWire` ohne Kennung (die Kurzbezeichnung `slug` bleibt für das Beispiel). */
type ScheduleDraft = Omit<ScheduleWire, 'id'>;

const TEXTS: ConfigTexts = {
  add: 'schedules.add',
  create: 'schedules.new',
  edit: 'schedules.edit',
};

/** Zeitpläne: Beginn, Intervall, Lauf, Aufgaben mit Häufigkeit, Live-Auswertung, Optionen und ein Beispiel für Automationen. */
export class SchedulesView extends ConfigView<ScheduleWire, ScheduleDraft> {
  static override styles = [
    ...ConfigView.styles,
    css`
      pre {
        margin: 0;
        padding: var(--tw-space-s);
        overflow-x: auto;
        border-radius: 8px;
        background: var(--tw-color-background);
        font-size: 0.85em;
      }
    `,
  ];

  protected readonly resource = 'schedule';
  protected readonly collection = 'schedules';
  protected readonly texts = TEXTS;
  readonly #plan = new PlanPreviewLoader(this);
  #planFor: ScheduleDraft | undefined;

  protected blank(snapshot: Snapshot): ScheduleDraft {
    return {
      name: '',
      start: defaultStart(snapshot.now),
      interval: INTERVAL_DEFAULT,
      automatic: false,
      run_days: DEFAULT_RUN_DAYS,
      entries: [],
      enabled: true,
      notify: true,
      skip_absent: true,
      archived: false,
      animations: DEFAULT_ANIMATIONS,
      slug: '',
    };
  }

  protected draftOf(schedule: ScheduleWire): ScheduleDraft {
    return {
      name: schedule.name,
      slug: schedule.slug,
      start: schedule.start,
      interval: schedule.interval,
      automatic: schedule.automatic,
      run_days: schedule.run_days,
      entries: schedule.entries,
      enabled: schedule.enabled,
      notify: schedule.notify,
      skip_absent: schedule.skip_absent,
      archived: schedule.archived,
      animations: animationsOf(schedule.animations),
    };
  }

  protected payload(draft: ScheduleDraft): object {
    return {
      name: draft.name,
      start: draft.start,
      interval: draft.interval,
      automatic: draft.automatic,
      run_days: draft.run_days,
      entries: draft.entries,
      enabled: draft.enabled,
      notify: draft.notify,
      skip_absent: draft.skip_absent,
      archived: draft.archived && !draft.enabled,
      animations: draft.animations,
    };
  }

  protected override canSave(): boolean {
    return !this.#plan.blocking;
  }

  /** Lässt die Planung bewerten, sobald sie sich im Entwurf ändert; ohne Entwurf ruht die Bewertung. */
  protected override willUpdate(): void {
    super.willUpdate();
    const draft = this._draft;
    const client = this.store.client;
    if (draft === this.#planFor) {
      return;
    }
    if (!draft) {
      this.#planFor = undefined;
      this.#plan.reset();
    } else if (client) {
      this.#planFor = draft;
      this.#plan.request(client, {
        interval: draft.interval,
        run_days: draft.run_days,
        entries: draft.entries,
      });
    }
  }

  protected card(schedule: ScheduleWire): TemplateResult {
    const state = schedule.archived
      ? this.text('schedules.archived')
      : schedule.enabled
        ? ''
        : this.text('schedules.disabled');
    const mode = this.text(
      schedule.automatic ? 'schedules.card.automatic' : 'schedules.card.manual',
    );
    return html`
      <strong>${schedule.name}</strong>
      <div class="muted">
        ${translate('schedules.card.start', this.language, {
          at: formatDateTime(schedule.start, this.language),
        })}
      </div>
      <div class="muted">${describeInterval(schedule.interval, this.language)}, ${mode}</div>
      <div class="muted">
        ${translate('schedules.card.run', this.language, {
          days: schedule.run_days,
          count: schedule.entries.length,
        })}
        ${state}
      </div>
    `;
  }

  protected form(draft: ScheduleDraft, snapshot: Snapshot): TemplateResult {
    const tasks = taskOptions(snapshot);
    return html`
      ${this.nameField(draft.name, (name) => {
        this.patch({ name });
      })}
      ${this.#timing(draft)}
      <tw-entry-editor
        .language=${this.language}
        .tasks=${tasks}
        .value=${draft.entries}
        .runDays=${draft.run_days}
        .error=${this.fieldError('entries')}
        @tw-change=${onChange<EntryWire[]>((entries) => {
          this.patch({ entries });
        })}
      ></tw-entry-editor>
      <tw-plan-preview
        .language=${this.language}
        .preview=${this.#plan.value}
        .tasks=${tasks}
        .people=${personOptions(snapshot)}
        .runDays=${draft.run_days}
        ?loading=${this.#plan.loading}
      ></tw-plan-preview>
      <div>
        ${this.toggle('schedules.enabled', 'enabled', draft.enabled)}
        ${this.toggle('schedules.notify', 'notify', draft.notify)}
        ${this.toggle('schedules.skip_absent', 'skip_absent', draft.skip_absent)}
      </div>
      ${this.#animations(draft.animations)} ${draft.slug ? this.#example(draft.slug) : nothing}
    `;
  }

  /** Beginn, Intervall, Art der Auslosung und Länge des Laufs. */
  #timing(draft: ScheduleDraft): TemplateResult {
    const error = this.fieldError('interval', 'run_days');
    return html`
      ${this.#start(draft)} ${this.#interval(draft.interval)} ${this.#mode(draft.automatic)}
      ${this.#run(draft)} ${error ? html`<div class="banner">${error}</div>` : nothing}
    `;
  }

  #start(draft: ScheduleDraft): TemplateResult {
    return html`<tw-field
      type="datetime-local"
      .label=${this.text('schedules.start')}
      .value=${localInput(draft.start)}
      .error=${this.fieldError('start')}
      @tw-change=${onChange<string>((value) => {
        this.patch({ start: fromLocalInput(value) });
      })}
    ></tw-field>`;
  }

  /** Abstand zwischen zwei Auslosungen: Anzahl und Einheit nebeneinander. */
  #interval(interval: IntervalWire): TemplateResult {
    const units = INTERVAL_UNITS.map((unit) => ({
      id: unit,
      label: this.text(`interval.unit.${unit}`),
    }));
    return html`<div class="pair">
      <tw-stepper
        .label=${this.text('schedules.interval')}
        .value=${interval.every}
        .min=${FORM_LIMITS.intervalEvery.min}
        .max=${FORM_LIMITS.intervalEvery.max}
        @tw-change=${onChange<number>((every) => {
          this.patch({ interval: { ...interval, every } });
        })}
      ></tw-stepper>
      <tw-select
        .label=${this.text('schedules.interval_unit')}
        .options=${units}
        .value=${interval.unit}
        @tw-change=${onChange<IntervalUnit>((unit) => {
          this.patch({ interval: { ...interval, unit } });
        })}
      ></tw-select>
    </div>`;
  }

  /** Automatisch (das System lost zu jedem Termin) oder manuell (ein Klick startet die Auslosung). */
  #mode(automatic: boolean): TemplateResult {
    const modes = SCHEDULE_MODES.map((mode) => ({
      id: mode,
      label: this.text(`schedules.mode.${mode}`),
    }));
    const mode: ScheduleMode = automatic ? 'automatic' : 'manual';
    return html`
      <tw-segmented
        .label=${this.text('schedules.mode')}
        .options=${modes}
        .value=${mode}
        @tw-change=${onChange<ScheduleMode>((next) => {
          this.patch({ automatic: next === 'automatic' });
        })}
      ></tw-segmented>
      <span class="muted">${this.text(`schedules.mode.${mode}.hint`)}</span>
    `;
  }

  /** Länge des Laufs, über den die Mindesthäufigkeit gilt. */
  #run(draft: ScheduleDraft): TemplateResult {
    return html`
      <tw-stepper
        .label=${this.text('schedules.run_days')}
        .value=${draft.run_days}
        .min=${FORM_LIMITS.runDays.min}
        .max=${FORM_LIMITS.runDays.max}
        @tw-change=${onChange<number>((run_days) => {
          this.patch({ run_days });
        })}
      ></tw-stepper>
      <span class="muted">
        ${translate('schedules.due_hint', this.language, {
          interval: describeInterval(draft.interval, this.language),
        })}
      </span>
    `;
  }

  /** Mehrfachauswahl der Animationen; bei mehreren wird bei jeder Auslosung zufällig eine genommen. */
  #animations(selected: readonly AnimationKind[]): TemplateResult {
    const options: readonly ChipOption[] = ANIMATION_KINDS.map((kind) => ({
      id: kind,
      label: this.text(`animation.${kind}` as TextKey),
    }));
    return html`
      <tw-chip-select
        .label=${this.text('schedules.animations')}
        .options=${options}
        .selected=${selected}
        .error=${this.fieldError('animations')}
        @tw-change=${onChange<AnimationKind[]>((animations) => {
          this.patch({ animations });
        })}
      ></tw-chip-select>
      <span class="muted">${this.text('schedules.animations.hint')}</span>
    `;
  }

  #example(slug: string): TemplateResult {
    return html`
      <div>
        <span class="label">${this.text('schedules.example')}</span>
        <pre>
action: ${SERVICE_DRAW}
data:
  schedule: ${slug}</pre>
        <pre>
trigger: event
event_type: ${EVENT_DRAWN_NAME}</pre>
      </div>
    `;
  }
}

defineOnce(VIEW_TAGS.schedules, SchedulesView);
