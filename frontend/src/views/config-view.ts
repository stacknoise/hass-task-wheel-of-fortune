import { LitElement, css, html, nothing } from 'lit';
import type { TemplateResult } from 'lit';
import { repeat } from 'lit/directives/repeat.js';

import { failureFor, parseFailure } from '../api/index.ts';
import type { ApiFailure, Snapshot } from '../api/index.ts';
import { baseStyles, formStyles, onChange, tokenStyles } from '../components/index.ts';
import '../components/index.ts';
import { FORM_LIMITS } from '../constants/index.ts';
import type { CollectionName, ConfigResource } from '../constants/index.ts';
import { translate, translateError } from '../i18n/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { StoreController } from '../state/index.ts';

/** Die Texte einer Konfigurationsansicht. */
export interface ConfigTexts {
  readonly add: TextKey;
  readonly create: TextKey;
  readonly edit: TextKey;
}

/**
 * Gemeinsame Ansicht zum Anlegen, Ändern und Löschen einer Art von Konfigurationsobjekten:
 * Karten, Formular im Dialog (`tw-dialog`), Löschen nach Rückfrage. Die Unterklassen liefern Karte, Formular und die Umwandlung
 * zwischen Objekt, Entwurf und Nachricht; Fehler des Backends zeigt diese Klasse an.
 */
export abstract class ConfigView<
  Wire extends { readonly id: string },
  Draft extends object,
> extends LitElement {
  static override properties = {
    language: { type: String },
    _draft: { state: true },
    _editId: { state: true },
    _failure: { state: true },
    _busy: { state: true },
    _confirm: { state: true },
  };

  static override styles = [
    tokenStyles,
    baseStyles,
    formStyles,
    css`
      .top {
        display: flex;
        justify-content: flex-end;
        margin-bottom: var(--tw-space-m);
      }
      .cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
        gap: var(--tw-space-m);
      }
      .card {
        text-align: left;
        padding: var(--tw-space-m);
        border-radius: var(--tw-radius);
        border: 2px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      .card > div {
        margin-top: var(--tw-space-s);
      }
      section.editor {
        display: grid;
        gap: var(--tw-space-field);
      }
      .buttons {
        display: flex;
        flex-wrap: wrap;
        gap: var(--tw-space-s);
      }
      .primary,
      .secondary,
      .danger {
        min-height: 40px;
        padding: 0 18px;
        border-radius: 20px;
        border: 1px solid var(--tw-color-divider);
        background: var(--tw-color-surface);
        cursor: pointer;
      }
      .primary {
        background: var(--tw-color-primary);
        border-color: var(--tw-color-primary);
        color: #fff;
      }
      .danger {
        color: var(--tw-color-error);
        border-color: var(--tw-color-error);
        margin-left: auto;
      }
      button:disabled {
        opacity: 0.5;
        cursor: default;
      }
      .banner {
        color: var(--tw-color-error);
      }
      .muted {
        color: var(--tw-color-text-muted);
      }
    `,
  ];

  declare language: string;
  declare _draft: Draft | undefined;
  declare _editId: string | undefined;
  declare _failure: ApiFailure | undefined;
  declare _busy: boolean;
  declare _confirm: boolean;

  protected readonly store = new StoreController(this);
  protected abstract readonly resource: ConfigResource;
  protected abstract readonly collection: CollectionName;
  protected abstract readonly texts: ConfigTexts;

  constructor() {
    super();
    this.language = '';
    this._busy = false;
    this._confirm = false;
  }

  /** Leerer Entwurf für ein neues Objekt. */
  protected abstract blank(snapshot: Snapshot): Draft;
  /** Entwurf aus einem vorhandenen Objekt. */
  protected abstract draftOf(item: Wire): Draft;
  /** Die Felder, die das Backend beim Anlegen und Ändern annimmt (ohne `id` und `slug`). */
  protected abstract payload(draft: Draft): object;
  protected abstract card(item: Wire, snapshot: Snapshot): TemplateResult;
  protected abstract form(draft: Draft, snapshot: Snapshot): TemplateResult;

  protected text(key: TextKey): string {
    return translate(key, this.language);
  }

  /** Ändert Felder des Entwurfs. */
  protected patch(partial: Partial<Draft>): void {
    if (this._draft) {
      this._draft = { ...this._draft, ...partial };
    }
  }

  /** Schalter für ein Feld des Entwurfs. */
  protected toggle(label: TextKey, key: keyof Draft, checked: boolean): TemplateResult {
    return html`<tw-toggle
      .label=${this.text(label)}
      .checked=${checked}
      @tw-change=${onChange<boolean>((value) => {
        this.patch({ [key]: value } as Partial<Draft>);
      })}
    ></tw-toggle>`;
  }

  /** Namensfeld, das der Entwurf aller Arten gemeinsam hat. */
  protected nameField(name: string, patchName: (name: string) => void): TemplateResult {
    return html`<tw-field
      .label=${this.text('form.name')}
      .value=${name}
      .maxlength=${FORM_LIMITS.nameMax}
      .error=${this.fieldError('name')}
      @tw-change=${onChange<string>(patchName)}
    ></tw-field>`;
  }

  /** Fehlertext, wenn der Fehler des Backends zu einem der Felder gehört. */
  protected fieldError(...fields: readonly string[]): string {
    const code = failureFor(this._failure, ...fields);
    return code === undefined ? '' : translateError(code, this.language);
  }

  /** Schließt das Formular, wenn das bearbeitete Objekt inzwischen gelöscht wurde. */
  protected override willUpdate(): void {
    if (this._editId !== undefined && !this.#items().some((item) => item.id === this._editId)) {
      this.#close();
    }
  }

  protected override render(): TemplateResult | typeof nothing {
    const snapshot = this.store.state?.snapshot;
    if (!snapshot) {
      return nothing;
    }
    const items = this.#items();
    return html`
      <div class="top">
        <button
          type="button"
          class="primary"
          @click=${() => {
            this.#open(undefined, this.blank(snapshot));
          }}
        >
          ${this.text(this.texts.add)}
        </button>
      </div>
      <div class="layout">
        <div class="cards">
          ${items.length === 0 ? html`<p class="muted">${this.text('form.empty')}</p>` : nothing}
          ${repeat(
            items,
            (item) => item.id,
            (item) => html`
              <button
                type="button"
                class="card"
                @click=${() => {
                  this.#open(item.id, this.draftOf(item));
                }}
              >
                ${this.card(item, snapshot)}
              </button>
            `,
          )}
        </div>
      </div>
      ${this._draft ? this.#editor(this._draft, snapshot) : nothing}
      ${this._confirm ? this.#confirmDelete() : nothing}
    `;
  }

  #items(): readonly Wire[] {
    return (this.store.state?.snapshot?.[this.collection] ?? []) as unknown as readonly Wire[];
  }

  #editor(draft: Draft, snapshot: Snapshot): TemplateResult {
    const creating = this._editId === undefined;
    const title = this.text(creating ? this.texts.create : this.texts.edit);
    return html`
      <tw-dialog
        language=${this.language}
        label=${title}
        @tw-cancel=${() => {
          this.#close();
        }}
      >
        <section class="editor">${this.form(draft, snapshot)} ${this.#banner()}</section>
        <div class="buttons" slot="actions">
          <button
            type="button"
            class="primary"
            ?disabled=${this._busy}
            @click=${() => {
              void this.#save();
            }}
          >
            ${this.text('form.save')}
          </button>
          <button
            type="button"
            class="secondary"
            @click=${() => {
              this.#close();
            }}
          >
            ${this.text('form.cancel')}
          </button>
          ${
            creating
              ? nothing
              : html`<button
                  type="button"
                  class="danger"
                  ?disabled=${this._busy}
                  @click=${() => {
                    this._confirm = true;
                  }}
                >
                  ${this.text('form.delete')}
                </button>`
          }
        </div>
      </tw-dialog>
    `;
  }

  #confirmDelete(): TemplateResult {
    return html`<tw-confirm-dialog
      language=${this.language}
      label=${this.text('form.delete')}
      question=${this.text('form.confirm_delete')}
      ?busy=${this._busy}
      @tw-confirm=${() => {
        void this.#remove();
      }}
      @tw-cancel=${() => {
        this._confirm = false;
      }}
    ></tw-confirm-dialog>`;
  }

  #banner(): TemplateResult | typeof nothing {
    const failure = this._failure;
    if (!failure) {
      return nothing;
    }
    const field = failure.field ? `${failure.field}: ` : '';
    return html`<div class="banner" role="alert">
      ${this.text('form.error')}${field}${translateError(failure.code, this.language)}
    </div>`;
  }

  #open(id: string | undefined, draft: Draft): void {
    this._editId = id;
    this._draft = draft;
    this._failure = undefined;
    this._confirm = false;
  }

  #close(): void {
    this._editId = undefined;
    this._draft = undefined;
    this._failure = undefined;
    this._confirm = false;
  }

  async #save(): Promise<void> {
    const client = this.store.client;
    if (!client || !this._draft) {
      return;
    }
    await this.#run(async () => {
      await client.saveConfig(this.resource, this._editId, this.payload(this._draft as Draft));
    });
  }

  async #remove(): Promise<void> {
    const client = this.store.client;
    if (!client || this._editId === undefined) {
      return;
    }
    const id = this._editId;
    await this.#run(() => client.deleteConfig(this.resource, id));
  }

  /** Führt den Aufruf aus; bei Erfolg schließt das Formular, bei Fehler zeigt es die Meldung des Backends. */
  async #run(call: () => Promise<unknown>): Promise<void> {
    this._busy = true;
    this._failure = undefined;
    try {
      await call();
      this.#close();
    } catch (error) {
      this._failure = parseFailure(error);
      this._confirm = false;
    } finally {
      this._busy = false;
    }
  }
}
