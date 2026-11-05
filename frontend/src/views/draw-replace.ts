import { html, nothing } from 'lit';
import type { TemplateResult } from 'lit';

import type { TaskReplacementWire } from '../api/index.ts';
import '../components/index.ts';
import { EMPTY_TEXT } from '../constants/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { canReplace } from '../state/index.ts';
import type { DrawSession, DrawState, TaskInfo } from '../state/index.ts';

/** Symbol des Knopfs „Austauschen“ (der Text steht als Beschriftung für Screenreader und Tooltip). */
const REPLACE_ICON = '⇄';

export interface ReplaceDialogContext {
  readonly language: string;
  /** Die Aufgabe, die aus der Runde genommen wird. */
  readonly task: TaskInfo | undefined;
  readonly tasks: ReadonlyMap<string, TaskInfo>;
  readonly options: readonly TaskReplacementWire[];
  readonly pick: string;
  readonly text: (key: TextKey) => string;
  readonly onPick: (taskId: string) => void;
  readonly onClose: () => void;
  readonly onApply: () => void;
}

function option(item: TaskReplacementWire, context: ReplaceDialogContext): TemplateResult {
  const { text } = context;
  return html`
    <label class="option ${item.doable ? '' : 'out'}">
      <input
        type="radio"
        name="replacement"
        .value=${item.task_id}
        ?disabled=${!item.doable}
        .checked=${item.doable && context.pick === item.task_id}
        @change=${() => {
          context.onPick(item.task_id);
        }}
      />
      <span>
        <strong>${context.tasks.get(item.task_id)?.name ?? item.task_id}</strong><br />
        <span class="muted"
          >${text(item.doable ? 'draw.replace.doable' : 'draw.replace.infeasible')}</span
        >
      </span>
    </label>
  `;
}

/** Dialog „Aufgabe austauschen“: der Admin wählt vor dem Start eine machbare Ersatzaufgabe. */
export function replaceDialog(context: ReplaceDialogContext): TemplateResult {
  const { text } = context;
  return html`
    <tw-dialog
      language=${context.language}
      label=${text('draw.replace.title')}
      @tw-cancel=${context.onClose}
    >
      <p><strong>${text('draw.replace.out')}</strong> ${context.task?.name ?? EMPTY_TEXT}</p>
      <fieldset class="options">
        <legend class="muted">${text('draw.replace.with')}</legend>
        ${
          context.options.length === 0
            ? html`<span class="muted">${text('draw.replace.none')}</span>`
            : context.options.map((item) => option(item, context))
        }
      </fieldset>
      <p class="muted">${text('draw.replace.hint')}</p>
      <div class="actions" slot="actions">
        <button class="button primary" ?disabled=${!context.pick} @click=${context.onApply}>
          ${text('draw.replace.apply')}
        </button>
        <button class="button" @click=${context.onClose}>${text('form.cancel')}</button>
      </div>
    </tw-dialog>
  `;
}

export interface ReplaceFlowDeps {
  readonly host: { readonly language: string; requestUpdate(): void };
  readonly session: () => DrawSession | undefined;
  readonly isAdmin: () => boolean;
  readonly text: (key: TextKey) => string;
}

/** Der Ablauf „Aufgabe austauschen“ in der Auslosung: Knopf je Aufgabe, Dialog, Tausch. */
export class ReplaceFlow {
  readonly #deps: ReplaceFlowDeps;
  /** Die Aufgabe, die gerade ausgetauscht wird (Dialog offen), sonst leer. */
  #replacing = EMPTY_TEXT;
  #options: readonly TaskReplacementWire[] = [];
  #pick = EMPTY_TEXT;

  constructor(deps: ReplaceFlowDeps) {
    this.#deps = deps;
  }

  /** Kann der Admin jetzt noch tauschen (Admin, vor dem ersten Dreh)? */
  available(state: DrawState): boolean {
    return canReplace(state) && this.#deps.isAdmin();
  }

  /** Der Knopf „Austauschen“ (nur Admin, nur vor dem Start). */
  button(state: DrawState, task: TaskInfo): TemplateResult | typeof nothing {
    if (!this.available(state)) {
      return nothing;
    }
    const label = this.#deps.text('draw.replace');
    return html`<button
      class="button icon"
      title=${label}
      aria-label="${label}: ${task.name}"
      @click=${() => void this.#open(task.id)}
    >
      ${REPLACE_ICON}
    </button>`;
  }

  /** Der Dialog, solange er offen ist und der Tausch noch erlaubt ist. */
  dialog(state: DrawState, tasks: ReadonlyMap<string, TaskInfo>): TemplateResult | typeof nothing {
    if (!this.#replacing || !canReplace(state)) {
      return nothing;
    }
    return replaceDialog({
      language: this.#deps.host.language,
      task: tasks.get(this.#replacing),
      tasks,
      options: this.#options,
      pick: this.#pick,
      text: this.#deps.text,
      onPick: (id) => {
        this.#set(this.#replacing, this.#options, id);
      },
      onClose: () => {
        this.#set(EMPTY_TEXT, this.#options, this.#pick);
      },
      onApply: () => {
        const from = this.#replacing;
        this.#set(EMPTY_TEXT, this.#options, this.#pick);
        void this.#deps.session()?.replaceTask(from, this.#pick);
      },
    });
  }

  async #open(taskId: string): Promise<void> {
    const options = (await this.#deps.session()?.replacements(taskId)) ?? [];
    this.#set(taskId, options, options.find((item) => item.doable)?.task_id ?? EMPTY_TEXT);
  }

  #set(replacing: string, options: readonly TaskReplacementWire[], pick: string): void {
    this.#replacing = replacing;
    this.#options = options;
    this.#pick = pick;
    this.#deps.host.requestUpdate();
  }
}
