import { css } from 'lit';
import type { CSSResult } from 'lit';

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
  .control {
    min-height: 40px;
    box-sizing: border-box;
    border: 1px solid var(--tw-color-divider);
    border-radius: 8px;
    background: var(--tw-color-surface);
    padding: 0 12px;
  }
`;
