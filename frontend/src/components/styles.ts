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
