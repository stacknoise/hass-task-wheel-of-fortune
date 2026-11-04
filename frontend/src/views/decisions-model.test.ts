import { describe, expect, it } from 'vitest';

import type { DecisionExchange, DecisionRecord, DecisionTask } from '../api/index.ts';
import type { TextKey } from '../i18n/index.ts';
import { DECISIONS } from './fixtures.testing.ts';
import {
  candidateLines,
  counts,
  exchangeText,
  outcomeOf,
  reasonText,
  showsRecord,
  tasksMatching,
} from './decisions-model.ts';

const [draw, exchange] = DECISIONS.entries as [
  DecisionRecord & { exchange: null },
  DecisionRecord & { exchange: DecisionExchange },
];
const [first, , garage] = draw.tasks as [DecisionTask, DecisionTask, DecisionTask];
const text = (key: TextKey, params?: Record<string, string | number>) =>
  `${key}${params ? JSON.stringify(params) : ''}`;

describe('Entscheidungslog-Modell', () => {
  it('zählt und filtert Aufgaben nach Ergebnis', () => {
    expect(counts(draw)).toEqual({ assigned: 2, unassigned: 1 });
    expect(outcomeOf(garage)).toBe('unassigned');
    expect(tasksMatching(draw, 'assigned')).toHaveLength(2);
    expect(tasksMatching(draw, 'all')).toHaveLength(3);
    expect(showsRecord(draw, 'unassigned')).toBe(true);
    expect(showsRecord(exchange, 'unassigned')).toBe(true);
  });

  it('ordnet Gewinner vor Rad vor Ausgeschlossenen', () => {
    const lines = candidateLines(first, 'de', text);
    expect(lines.map((l) => l.name)).toEqual(['Anna', 'Ben', 'Cara']);
    expect(lines.map((l) => l.tone)).toEqual(['success', 'info', 'warning']);
  });

  it('übersetzt bekannte Gründe und zeigt unbekannte unverändert', () => {
    expect(reasonText('absent', 'de')).toBe('Abwesend');
    expect(reasonText('zukunft', 'de')).toBe('zukunft');
  });

  it('beschreibt einen Admin-Austausch', () => {
    expect(exchangeText(exchange.exchange, text)).toContain('log.exchange');
  });
});
