import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import { personsOf } from '../api/index.ts';
import type { AreaOption, Snapshot, TaskWire } from '../api/index.ts';
import { onChange } from '../components/index.ts';
import '../components/index.ts';
import {
  DEFAULT_MIN_LOAD,
  DEFAULT_TASK_POINTS,
  FORM_LIMITS,
  MIN_LOADS,
  VIEW_TAGS,
} from '../constants/index.ts';
import type { Load } from '../constants/index.ts';
import { translate } from '../i18n/index.ts';
import { taskUsage } from '../state/index.ts';
import { personOptions } from './chip-options.ts';
import { ConfigView } from './config-view.ts';
import { roomTags } from './room.ts';
import type { ConfigTexts } from './config-view.ts';
import { defineOnce } from '../components/define.ts';

/** Formularstand: wie `TaskWire` ohne Kennung. */
type TaskDraft = Omit<TaskWire, 'id'>;

const TEXTS: ConfigTexts = { add: 'tasks.add', create: 'tasks.new', edit: 'tasks.edit' };

/** Aufgaben: erlaubte Personen, Punkte und Zusatzregeln; Häufigkeit und Frist legt der Zeitplan fest. */
export class TasksView extends ConfigView<TaskWire, TaskDraft> {
  protected readonly resource = 'task';
  protected readonly collection = 'tasks';
  protected readonly texts = TEXTS;

  protected blank(snapshot: Snapshot): TaskDraft {
    return {
      name: '',
      allowed: personsOf(snapshot).map((person) => person.id),
      points: DEFAULT_TASK_POINTS,
      no_repeat: false,
      respect_absence: true,
      swap_allowed: true,
      min_load: DEFAULT_MIN_LOAD,
      area_ids: [],
    };
  }

  protected draftOf(task: TaskWire): TaskDraft {
    return {
      name: task.name,
      allowed: task.allowed,
      points: task.points,
      no_repeat: task.no_repeat,
      respect_absence: task.respect_absence,
      swap_allowed: task.swap_allowed,
      min_load: task.min_load,
      area_ids: task.area_ids,
    };
  }

  protected payload(draft: TaskDraft): object {
    return draft;
  }

  protected card(task: TaskWire, snapshot: Snapshot): TemplateResult {
    return html`
      <strong>${task.name}</strong>
      <div class="muted">${task.points} ${this.text('tasks.points_short')}</div>
      <div class="muted">
        ${translate('tasks.card.schedules', this.language, {
          count: taskUsage(snapshot, task.id).length,
        })}
      </div>
      ${this.#room(task.area_ids)}
    `;
  }

  protected form(draft: TaskDraft, snapshot: Snapshot): TemplateResult {
    return html`
      ${this.nameField(draft.name, (name) => {
        this.patch({ name });
      })}
      <tw-chip-select
        .label=${this.text('tasks.allowed')}
        .options=${personOptions(snapshot)}
        .selected=${draft.allowed}
        .error=${this.fieldError('allowed')}
        @tw-change=${onChange<string[]>((allowed) => {
          this.patch({ allowed });
        })}
      ></tw-chip-select>
      <tw-stepper
        .label=${this.text('tasks.points')}
        .value=${draft.points}
        .min=${FORM_LIMITS.points.min}
        .max=${FORM_LIMITS.points.max}
        @tw-change=${onChange<number>((points) => {
          this.patch({ points });
        })}
      ></tw-stepper>
      ${this.#areaSelect(draft.area_ids)} ${this.#minLoad(draft.min_load)} ${this.#rules(draft)}
      ${this.#usage(snapshot)}
    `;
  }

  /** In welchen Zeitplänen die Aufgabe vorkommt und wie oft; die Häufigkeit stellt man im Zeitplan ein. */
  #usage(snapshot: Snapshot): TemplateResult {
    const usage = this._editId === undefined ? [] : taskUsage(snapshot, this._editId);
    return html`
      <div>
        <span class="label">${this.text('tasks.usage')}</span>
        ${
          usage.length === 0
            ? html`<span class="muted">${this.text('tasks.usage.none')}</span>`
            : html`<ul>
                ${usage.map(
                  ({ scheduleId, scheduleName, entry }) =>
                    html`<li class="muted" data-schedule=${scheduleId}>
                      ${translate(
                        entry.mode === 'every_draw'
                          ? 'tasks.usage.every_draw'
                          : 'tasks.usage.min_count',
                        this.language,
                        { name: scheduleName, count: entry.min_count },
                      )}
                    </li>`,
                )}
              </ul>`
        }
      </div>
    `;
  }

  #areas(): readonly AreaOption[] {
    return this.store.client?.areas() ?? [];
  }

  #room(areaIds: readonly string[]): TemplateResult | typeof nothing {
    return roomTags(this.store.areaNames(), areaIds, this.text('common.unknownArea'));
  }

  /** Alle Räume; ein vergebener, inzwischen gelöschter Raum bleibt wählbar, damit nichts still verfällt. */
  #areaOptions(selected: readonly string[]): readonly AreaOption[] {
    const areas = this.#areas();
    const known = new Set(areas.map((area) => area.id));
    const stale = selected
      .filter((id) => !known.has(id))
      .map((id) => ({ id, label: this.text('common.unknownArea') }));
    return [...stale, ...areas];
  }

  #areaSelect(selected: readonly string[]): TemplateResult {
    return html`
      <tw-chip-select
        .label=${this.text('tasks.area')}
        .options=${this.#areaOptions(selected)}
        .selected=${selected}
        .error=${this.fieldError('area_ids')}
        @tw-change=${onChange<string[]>((area_ids) => {
          this.patch({ area_ids });
        })}
      ></tw-chip-select>
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
