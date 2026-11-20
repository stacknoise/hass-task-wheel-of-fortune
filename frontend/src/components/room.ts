import { LitElement, css, html, nothing, unsafeCSS } from 'lit';
import type { TemplateResult } from 'lit';

import { COMPONENT_TAGS, ROOM_COLORS, ROOM_DOT_COLOR } from '../constants/index.ts';
import { baseStyles, tokenStyles } from './styles.ts';
import { defineOnce } from './define.ts';
import { roomHue } from './room-color.ts';

const ROOM_DOT = unsafeCSS(ROOM_DOT_COLOR);

/** Raum einer Aufgabe als Chip (Kontur mit farbigem Punkt); ohne Namen wird nichts gezeigt. */
export class TwRoom extends LitElement {
  static override properties = { name: { type: String } };

  static override styles = [
    tokenStyles,
    baseStyles,
    css`
      :host {
        display: inline-flex;
        align-items: center;
        gap: var(--tw-space-xs);
        white-space: nowrap;
        max-width: 100%;
        box-sizing: border-box;
        margin: 0 var(--tw-space-xs) var(--tw-space-xs) 0;
        padding: 0 var(--tw-space-s) 0 var(--tw-space-s);
        font-size: 0.8em;
        line-height: 1.6;
        color: var(--tw-color-text-muted);
        border: 1px solid
          color-mix(in srgb, ${ROOM_DOT} ${ROOM_COLORS.borderMixPercent}%, var(--tw-color-divider));
        border-radius: 1em;
      }
      :host([hidden]) {
        display: none;
      }
      .dot {
        flex: none;
        width: 0.6em;
        height: 0.6em;
        border-radius: 50%;
        background: ${ROOM_DOT};
      }
      .label {
        overflow: hidden;
        text-overflow: ellipsis;
      }
    `,
  ];

  declare name: string;

  constructor() {
    super();
    this.name = '';
  }

  protected override render(): TemplateResult | typeof nothing {
    if (!this.name) {
      return nothing;
    }
    this.style.setProperty('--tw-room-hue', String(roomHue(this.name)));
    return html`<span class="dot" aria-hidden="true"></span
      ><span class="label">${this.name}</span>`;
  }
}

defineOnce(COMPONENT_TAGS.room, TwRoom);

/** Die Räume als Chips; überall dort, wo Räume gezeigt werden. Ohne Räume nichts. */
export function roomChips(names: readonly string[]): TemplateResult | typeof nothing {
  return names.length > 0
    ? html`${names.map((name) => html`<tw-room .name=${name}></tw-room>`)}`
    : nothing;
}
