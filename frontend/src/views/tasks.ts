import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { personsOf } from '../api/index.ts';
import type { AreaOption, Snapshot, TaskWire } from '../api/index.ts';
import { describeFrequency, onChange } from '../components/index.ts';
import type { ChipOption } from '../components/index.ts';
import '../components/index.ts';
import {
  DEFAULT_MIN_LOAD,
  DEFAULT_TASK_DUE_DAYS,
  DEFAULT_TASK_POINTS,
  FORM_LIMITS,
  MIN_LOADS,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { Load } from '../constants/index.ts';
import { FREQUENCY_BUILDERS, areaNames } from '../state/index.ts';
import type { FrequencyWire } from '../state/index.ts';
import { ConfigView } from './config-view.ts';
import { roomTag } from './room.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

interface TaskDraft {
  readonly name: string;
  readonly allowed: readonly string[];
  readonly frequency: FrequencyWire;
  readonly points: number;
  readonly due_days: number;
  readonly no_repeat: boolean;
  readonly respect_absence: boolean;
  readonly swap_allowed: boolean;
  readonly min_load: Load;
  /** Kennung des Raums; leer = kein Raum. */
  readonly area_id: string;
}

const TEXTS: ConfigTexts = { add: 'tasks.add', create: 'tasks.new', edit: 'tasks.edit' };

/** Aufgaben: erlaubte Personen, Häufigkeit mit Zeitstrahl, Punkte, Frist und Zusatzregeln. */
export class TasksView extends ConfigView<TaskWire, TaskDraft> {
  protected readonly resource = 'task';
  protected readonly collection = 'tasks';
  protected readonly texts = TEXTS;

  protected blank(snapshot: Snapshot): TaskDraft {
    return {
      name: '',
      allowed: personsOf(snapshot).map((person) => person.id),
      frequency: FREQUENCY_BUILDERS.every_round(),
      points: DEFAULT_TASK_POINTS,
      due_days: DEFAULT_TASK_DUE_DAYS,
      no_repeat: false,
      respect_absence: true,
      swap_allowed: true,
      min_load: DEFAULT_MIN_LOAD,
      area_id: '',
    };
  }

  protected draftOf(task: TaskWire): TaskDraft {
    return {
      name: task.name,
      allowed: task.allowed,
      frequency: task.frequency,
      points: task.points,
      due_days: task.due_days,
      no_repeat: task.no_repeat,
      respect_absence: task.respect_absence,
      swap_allowed: task.swap_allowed,
      min_load: task.min_load,
      area_id: task.area_id ?? '',
    };
  }

  protected payload(draft: TaskDraft): object {
    return { ...draft, area_id: draft.area_id || null };
  }

  protected card(task: TaskWire): TemplateResult {
    return html`
      <strong>${task.name}</strong>
      <div class="muted">
        ${task.points} ${this.text('tasks.points_short')} · ${task.due_days}
        ${this.text('tasks.days_short')}
      </div>
      <div class="muted">${describeFrequency(task.frequency, this.language)}</div>
      ${this.#room(task.area_id)}
    `;
  }

  protected form(draft: TaskDraft, snapshot: Snapshot): TemplateResult {
    const people: readonly ChipOption[] = personsOf(snapshot).map((person) => ({
      id: person.id,
      label: person.name,
      color: person.color,
    }));
    return html`
      ${this.nameField(draft.name, (name) => {
        this.patch({ name });
      })}
      <tw-chip-select
        .label=${this.text('tasks.allowed')}
        .options=${people}
        .selected=${draft.allowed}
        .error=${this.fieldError('allowed')}
        @tw-change=${onChange<string[]>((allowed) => {
          this.patch({ allowed });
        })}
      ></tw-chip-select>
      <tw-frequency-editor
        .language=${this.language}
        .value=${draft.frequency}
        @tw-change=${onChange<FrequencyWire>((frequency) => {
          this.patch({ frequency });
        })}
      ></tw-frequency-editor>
      <div class="pair">
        <tw-stepper
          .label=${this.text('tasks.points')}
          .value=${draft.points}
          .min=${FORM_LIMITS.points.min}
          .max=${FORM_LIMITS.points.max}
          @tw-change=${onChange<number>((points) => {
            this.patch({ points });
          })}
        ></tw-stepper>
        <tw-stepper
          .label=${this.text('tasks.due_days')}
          .value=${draft.due_days}
          .min=${FORM_LIMITS.dueDays.min}
          .max=${FORM_LIMITS.dueDays.max}
          @tw-change=${onChange<number>((due_days) => {
            this.patch({ due_days });
          })}
        ></tw-stepper>
      </div>
      ${this.#areaSelect(draft.area_id)} ${this.#minLoad(draft.min_load)} ${this.#rules(draft)}
    `;
  }

  #areas(): readonly AreaOption[] {
    return this.store.client?.areas() ?? [];
  }

  #room(areaId: string | null): TemplateResult | typeof nothing {
    return roomTag(areaNames(this.#areas()), areaId, this.text('common.unknownArea'));
  }

  /** Alle Räume; ein vergebener, inzwischen gelöschter Raum bleibt wählbar, damit nichts still verfällt. */
  #areaOptions(value: string): readonly AreaOption[] {
    const areas = this.#areas();
    const none = { id: '', label: this.text('tasks.area.none') };
    const stale = value && !areas.some((area) => area.id === value);
    return [
      none,
      ...(stale ? [{ id: value, label: this.text('common.unknownArea') }] : []),
      ...areas,
    ];
  }

  #areaSelect(value: string): TemplateResult {
    return html`
      <tw-select
        .label=${this.text('tasks.area')}
        .options=${this.#areaOptions(value)}
        .value=${value}
        @tw-change=${onChange<string>((area_id) => {
          this.patch({ area_id });
        })}
      ></tw-select>
    `;
  }

  #minLoad(value: Load): TemplateResult {
    return html`
      <tw-select
        .label=${this.text('tasks.min_load')}
        .options=${MIN_LOADS.map((load) => ({
          id: load,
          label: this.text(`tasks.min_load.${load}`),
        }))}
        .value=${value}
        @tw-change=${onChange<Load>((min_load) => {
          this.patch({ min_load });
        })}
      ></tw-select>
    `;
  }

  #rules(draft: TaskDraft): TemplateResult {
    return html`
      <div>
        <span class="label">${this.text('tasks.rules')}</span>
        ${this.toggle('tasks.no_repeat', 'no_repeat', draft.no_repeat)}
        ${this.toggle('tasks.respect_absence', 'respect_absence', draft.respect_absence)}
        ${this.toggle('tasks.swap_allowed', 'swap_allowed', draft.swap_allowed)}
      </div>
    `;
  }
}

defineOnce(VIEW_TAGS.tasks, TasksView);
