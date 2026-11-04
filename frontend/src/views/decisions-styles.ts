import { css } from 'lit';
import type { CSSResult } from 'lit';

/** Aussehen des Entscheidungslogs: aufklappbare Einträge und Aufgaben, Zeilen je Person. */
export const decisionStyles: CSSResult = css`
  .head .full {
    flex: 1 1 100%;
    margin: 0;
  }
  .filters {
    display: flex;
    flex-direction: column;
    gap: var(--tw-space-m);
  }
  details > summary {
    display: flex;
    align-items: center;
    gap: var(--tw-space-m);
    cursor: pointer;
    list-style: none;
  }
  details > summary::-webkit-details-marker {
    display: none;
  }
  .titles {
    display: flex;
    flex-direction: column;
  }
  .chevron {
    transition: transform var(--tw-duration);
  }
  details[open] > summary > .chevron {
    transform: rotate(180deg);
  }
  .task {
    margin-top: var(--tw-space-s);
    padding-top: var(--tw-space-s);
    border-top: 1px solid var(--tw-color-divider);
  }
  .cand {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--tw-space-s) var(--tw-space-m);
    padding: var(--tw-space-s) 0;
  }
  .who {
    display: inline-flex;
    align-items: center;
    gap: var(--tw-space-s);
    min-width: 8em;
  }
  .why {
    color: var(--tw-color-text-muted);
  }
`;
