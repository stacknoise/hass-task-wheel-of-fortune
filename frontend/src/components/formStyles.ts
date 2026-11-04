import { css, unsafeCSS } from 'lit';
import type { CSSResult } from 'lit';

/** Mindestbreite eines Feldes in einer Zeile mit mehreren Feldern; darunter bricht die Zeile um. */
const PAIR_MIN_WIDTH = '150px';

/** Gemeinsame Gestaltung der Formularbausteine: Beschriftung, Fehlertext, Bedienelemente. */
export const formStyles: CSSResult = css`
  .label {
    display: block;
    font-size: 0.85em;
    font-weight: 500;
    margin-bottom: 4px;
  }
  .error {
    color: var(--tw-color-error);
    font-size: 0.85em;
    margin-top: 4px;
  }
  button,
  input,
  select {
    font: inherit;
    color: inherit;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid var(--tw-color-primary);
    outline-offset: 2px;
  }
  .pair {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(${unsafeCSS(PAIR_MIN_WIDTH)}, 1fr));
    gap: var(--tw-space-field);
  }
  .control {
    min-height: 40px;
    box-sizing: border-box;
    border: 1px solid var(--tw-color-divider);
    border-radius: 8px;
    background: var(--tw-color-surface);
    padding: 0 12px;
  }
`;

/** Gemeinsamer Feldabstand für Bausteine, die mehrere Felder untereinander zeigen (Editoren). */
export const stackStyles: CSSResult = css`
  :host {
    display: grid;
    gap: var(--tw-space-field);
  }
`;
