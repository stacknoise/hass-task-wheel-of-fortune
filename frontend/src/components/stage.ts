import { LitElement, css, html } from 'lit';
import type { PropertyValues, TemplateResult } from 'lit';

import { DEFAULT_ANIMATIONS, STAGE_TAG, STAGE_TAGS } from '../constants/index.ts';
import type { AnimationKind } from '../constants/index.ts';
import type { Stage } from './stage-base.ts';
import type { WheelSegment } from './wheel-geometry.ts';

/**
 * Bühne der Auslosung: zeigt je nach `kind` Rad, Lostrommel, Slot-Machine, Plinko oder Scheinwerfer.
 * Die Tabelle `STAGE_TAGS` ist die Registry; eine neue Art braucht nur einen Eintrag dort.
 */
export class TwStage extends LitElement {
  static override properties = {
    kind: { type: String },
    segments: { attribute: false },
    label: { type: String },
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

  #stage: Stage | undefined;
  #stageKind: AnimationKind | undefined;

  constructor() {
    super();
    this.kind = DEFAULT_ANIMATIONS[0] ?? 'wheel';
    this.segments = [];
    this.label = '';
  }

  /** Spielt die Animation der gewählten Art zum Gewinner `id`. */
  async spinTo(id: string): Promise<void> {
    await this.updateComplete;
    await this.#stage?.spinTo(id);
  }

  protected override willUpdate(changed: PropertyValues<this>): void {
    if (this.#stageKind !== this.kind) {
      this.#stage = document.createElement(STAGE_TAGS[this.kind]) as Stage;
      this.#stageKind = this.kind;
    }
    if (this.#stage && (changed.has('segments') || changed.has('label') || changed.has('kind'))) {
      this.#stage.segments = this.segments;
      this.#stage.label = this.label;
    }
  }

  protected override render(): TemplateResult {
    return html`${this.#stage}`;
  }
}

customElements.define(STAGE_TAG, TwStage);
