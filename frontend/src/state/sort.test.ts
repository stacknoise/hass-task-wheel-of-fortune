import { describe, expect, it } from 'vitest';

import type { Snapshot } from '../api/index.ts';
import { sortSnapshot, sortedByName } from './sort.ts';

const names = (items: readonly object[]): unknown[] =>
  items.map((item) => (item as { name?: unknown }).name);

describe('sortedByName', () => {
  it('ordnet ohne Groß-/Kleinschreibung', () => {
    const items = [
      { id: '1', name: 'bett' },
      { id: '2', name: 'Abwasch' },
      { id: '3', name: 'Cola' },
    ];
    expect(names(sortedByName(items, 'en'))).toEqual(['Abwasch', 'bett', 'Cola']);
  });
  it('ordnet Umlaute nach der Sprache', () => {
    const items = [
      { id: '1', name: 'Zimmer' },
      { id: '2', name: 'Äpfel' },
      { id: '3', name: 'Ofen' },
    ];
    expect(names(sortedByName(items, 'de'))).toEqual(['Äpfel', 'Ofen', 'Zimmer']);
    expect(names(sortedByName(items, 'sv'))).toEqual(['Ofen', 'Zimmer', 'Äpfel']);
  });
  it('ordnet Zahlen nach ihrem Wert', () => {
    const items = [
      { id: '1', name: 'Zimmer 10' },
      { id: '2', name: 'Zimmer 2' },
    ];
    expect(names(sortedByName(items, 'de'))).toEqual(['Zimmer 2', 'Zimmer 10']);
  });
  it('behält die Liste, wenn sie schon geordnet ist, und verändert das Original nie', () => {
    const ordered = [
      { id: '1', name: 'A' },
      { id: '2', name: 'b' },
    ];
    expect(sortedByName(ordered, 'de')).toBe(ordered);
    const messy = [
      { id: '1', name: 'b' },
      { id: '2', name: 'A' },
    ];
    sortedByName(messy, 'de');
    expect(names(messy)).toEqual(['b', 'A']);
  });
  it('stellt Objekte ohne Namen nach vorn', () => {
    expect(names(sortedByName([{ id: '1', name: 'A' }, { id: '2' }], 'de'))).toEqual([
      undefined,
      'A',
    ]);
  });
});

describe('sortSnapshot', () => {
  it('ordnet Personen, Aufgaben und Zeitpläne, nicht die Zuteilungen', () => {
    const snapshot = {
      persons: [
        { id: 'p1', name: 'Zoe' },
        { id: 'p2', name: 'anna' },
      ],
      tasks: [
        { id: 't1', name: 'Müll' },
        { id: 't2', name: 'Bad' },
      ],
      schedules: [
        { id: 's1', name: 'Woche' },
        { id: 's2', name: 'Abend' },
      ],
      assignments: [
        { id: 'a1', name: 'z' },
        { id: 'a2', name: 'a' },
      ],
    } as unknown as Snapshot;
    const sorted = sortSnapshot(snapshot, 'de');
    expect(names(sorted.persons)).toEqual(['anna', 'Zoe']);
    expect(names(sorted.tasks)).toEqual(['Bad', 'Müll']);
    expect(names(sorted.schedules)).toEqual(['Abend', 'Woche']);
    expect(sorted.assignments).toBe(snapshot.assignments);
  });
});
