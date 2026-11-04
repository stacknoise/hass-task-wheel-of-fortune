import { LitElement, css, html } from 'lit';
import type { TemplateResult } from 'lit';

import { DEFAULT_ANIMATIONS, STAGE_TAG, STAGE_TAGS } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import type { Stage } from './stage-base.ts';
import type { WheelSegment } from './wheel-geometry.ts';
import { defineOnce } from './define.ts';

/**
 * Bühne der Auslosung: zeigt je nach `kind` Rad, Lostrommel, Slot-Machine, Plinko, Scheinwerfer, Rubbellose, Eilmeldung oder Oscar-Verleihung.
 * Die Tabelle `STAGE_TAGS` ist die Registry; eine neue Art braucht nur einen Eintrag dort.
 */
export class TwStage extends LitElement {
  static override properties = {
    kind: { type: String },
    segments: { attribute: false },
    label: { type: String },
    taskName: { type: String },
    language: { type: String },
  };

  static override styles = css`
    :host {
      display: block;
    }
    * {
      display: block;
      width: 100%;
      height: 100%;
    }
  `;

  declare kind: AnimationKind;
  declare segments: readonly WheelSegment[];
  declare label: string;
  declare taskName: string;
  declare language: string;

  #stage: Stage | undefined;
  #stageKind: AnimationKind | undefined;

  constructor() {
    super();
    this.kind = DEFAULT_ANIMATIONS[0] ?? 'wheel';
    this.segments = [];
    this.label = '';
    this.taskName = '';
    this.language = '';
  }

  /** Spielt die Animation der gewählten Art zum Gewinner `id`. */
  async spinTo(id: string): Promise<void> {
    await this.updateComplete;
    await this.#stage?.spinTo(id);
  }

  protected override willUpdate(): void {
    if (this.#stageKind !== this.kind) {
      this.#stage = document.createElement(STAGE_TAGS[this.kind]) as Stage;
      this.#stageKind = this.kind;
    }
    if (this.#stage) {
      this.#stage.segments = this.segments;
      this.#stage.label = this.label;
      this.#stage.taskName = this.taskName;
      this.#stage.language = this.language;
    }
  }

  protected override render(): TemplateResult {
    return html`${this.#stage}`;
  }
}

defineOnce(STAGE_TAG, TwStage);
