import { css } from 'lit';
import type { CSSResult } from 'lit';

import { baseStyles, tokenStyles } from '../components/index.ts';

/** Gestaltung der Auslosung (Karte links, Bühne rechts). */
export const drawStyles: CSSResult[] = [
  tokenStyles,
  baseStyles,
  css`
    .layout {
      display: flex;
      flex-wrap: wrap;
      gap: var(--tw-space-m);
      align-items: flex-start;
    }
    .card {
      flex: 1 1 260px;
      max-width: 340px;
      background: var(--tw-color-surface);
      border: 1px solid var(--tw-color-divider);
      border-radius: var(--tw-radius);
      padding: var(--tw-space-s) 0;
    }
    .card > * {
      padding: var(--tw-space-s) var(--tw-space-m);
    }
    .card > ul {
      padding: 0;
    }
    label,
    .muted {
      color: var(--tw-color-text-muted);
      font-size: 0.85em;
    }
    select {
      display: block;
      width: 100%;
      min-height: 44px;
      margin-top: var(--tw-space-s);
      padding: 0 var(--tw-space-s);
      font: inherit;
    }
    h2 {
      margin: 0;
      font-size: 1.15em;
      font-weight: 500;
    }
    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }
    .task {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: var(--tw-space-s);
      padding: var(--tw-space-m);
      border-top: 1px solid var(--tw-color-divider);
    }
    .task.current {
      background: var(--tw-color-background);
    }
    .status {
      font-weight: 500;
      white-space: nowrap;
    }
    .button {
      min-height: 44px;
      white-space: nowrap;
      padding: 0 var(--tw-space-l);
      border: 1px solid var(--tw-color-divider);
      border-radius: 22px;
      background: var(--tw-color-surface);
      color: var(--tw-color-primary);
      font: inherit;
      font-weight: 500;
      cursor: pointer;
    }
    .button.primary {
      background: var(--tw-color-primary);
      border-color: var(--tw-color-primary);
      color: var(--tw-color-on-primary);
    }
    .button:disabled {
      opacity: 0.5;
      cursor: default;
    }
    .stage {
      flex: 999 1 520px;
      min-width: 0;
      position: relative;
      overflow: hidden;
      display: flex;
      flex-wrap: wrap;
      gap: var(--tw-space-l);
      align-items: center;
      justify-content: center;
      padding: var(--tw-space-l);
      border-radius: var(--tw-radius);
      background: transparent;
    }
    .heading {
      flex: 1 1 100%;
      text-align: center;
    }
    .eyebrow {
      display: block;
      color: var(--tw-color-text-muted);
      font-size: 0.8em;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .title {
      font-size: 1.9em;
      font-weight: 900;
    }
    .wheel-box {
      position: relative;
      width: 380px;
      max-width: 100%;
      aspect-ratio: 1 / 1;
    }
    tw-wheel {
      position: absolute;
      inset: 0;
    }
    .hub {
      position: absolute;
      left: 50%;
      top: 50%;
      width: 104px;
      height: 104px;
      margin: -52px 0 0 -52px;
      border-radius: 50%;
      border: 5px solid var(--tw-color-surface);
      background: var(--tw-color-primary);
      color: var(--tw-color-on-primary);
      font: inherit;
      font-weight: 900;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      cursor: pointer;
    }
    .hub:disabled {
      background: var(--tw-color-text-muted);
      cursor: default;
    }
    .people {
      flex: 1 1 220px;
      max-width: 280px;
    }
    .person {
      display: flex;
      align-items: center;
      gap: var(--tw-space-s);
      margin-top: var(--tw-space-s);
    }
    .person.out {
      opacity: 0.45;
    }
    .avatar {
      flex: none;
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid var(--tw-color-surface);
      border-radius: 50%;
      color: #ffffff;
      font-weight: 700;
    }
    .result {
      flex: 1 1 100%;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: var(--tw-space-m);
      padding: var(--tw-space-m);
      border-radius: var(--tw-radius);
      background: var(--tw-color-surface);
      color: var(--tw-color-text);
      position: relative;
    }
    .result .avatar {
      width: 56px;
      height: 56px;
      font-size: 1.5em;
      color: #ffffff;
    }
    .result .text {
      flex: 1 1 200px;
    }
    .done {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: var(--tw-space-m);
      padding: var(--tw-space-l);
      background: var(--tw-color-background);
    }
    .summary {
      width: 100%;
      max-width: 420px;
    }
    .summary li {
      display: flex;
      justify-content: space-between;
      gap: var(--tw-space-s);
      margin-top: var(--tw-space-s);
      padding: var(--tw-space-s) var(--tw-space-m);
      border: 1px solid var(--tw-color-divider);
      border-radius: var(--tw-radius);
      background: var(--tw-color-surface);
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--tw-space-s);
    }
    .card .actions {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
    }
    .card .button {
      width: 100%;
    }
    .people .hint {
      display: block;
      margin-top: var(--tw-space-l);
    }
    .error {
      color: var(--tw-color-error);
    }
  `,
];
