import { css, unsafeCSS } from 'lit';
import type { CSSResult } from 'lit';

import { TOKENS } from '../constants/index.ts';

const DECLARATION_END = ';\n';

/** Die Design-Tokens als Eigenschaften des Hosts (Werte stammen aus `constants/tokens.ts`). */
export const tokenStyles: CSSResult = unsafeCSS(
  `:host {\n${Object.entries(TOKENS)
    .map(([name, value]) => `${name}: ${value}`)
    .join(DECLARATION_END)}${DECLARATION_END}}`,
);

/** Gemeinsame Grundgestaltung der Komponenten. */
export const baseStyles: CSSResult = css`
  :host {
    display: block;
    color: var(--tw-color-text);
    box-sizing: border-box;
  }
`;

/** Gemeinsame Gestaltung der Ansichten: Karten, Überschriften, Hinweise, Schaltflächen, Tabellen. */
export const viewStyles: CSSResult = css`
  .card {
    background: var(--tw-color-surface);
    border: 1px solid var(--tw-color-divider);
    border-radius: var(--tw-radius);
    padding: var(--tw-space-m);
    margin-bottom: var(--tw-space-m);
  }
  h2 {
    margin: 0 0 var(--tw-space-s);
    font-size: 1.15em;
    font-weight: 500;
  }
  .muted {
    color: var(--tw-color-text-muted);
  }
  .empty {
    color: var(--tw-color-text-muted);
    padding: var(--tw-space-m) 0;
  }
  .error {
    color: var(--tw-color-error);
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--tw-space-s) var(--tw-space-m);
  }
  .nowrap {
    flex-wrap: nowrap;
  }
  .fixed {
    flex: none;
    white-space: nowrap;
  }
  .grow {
    flex: 1 1 auto;
    min-width: 0;
  }
  button.action {
    min-height: 36px;
    padding: 0 16px;
    border: 1px solid var(--tw-color-divider);
    border-radius: 18px;
    background: var(--tw-color-surface);
    color: var(--tw-color-primary);
    font: inherit;
    cursor: pointer;
  }
  button.action:disabled {
    color: var(--tw-color-text-muted);
    cursor: not-allowed;
  }
  button.primary {
    background: var(--tw-color-primary);
    border-color: var(--tw-color-primary);
    color: var(--tw-color-on-primary);
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th {
    text-align: left;
    font-weight: 500;
    color: var(--tw-color-text-muted);
  }
  th,
  td {
    padding: var(--tw-space-s);
  }
  tr + tr td {
    border-top: 1px solid var(--tw-color-divider);
  }
  .scroll {
    overflow-x: auto;
  }
`;
