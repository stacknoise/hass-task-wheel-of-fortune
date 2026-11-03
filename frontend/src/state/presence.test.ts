import { describe, expect, it } from 'vitest';

import type { AbsenceWire } from '../api/index.ts';
import {
  dateOfDay,
  dayNumber,
  dayOf,
  fromLocalInput,
  localInput,
  timeInput,
  weekdayOf,
} from './dates.ts';
import { isPresent, presencePreview } from './presence.ts';

const MONDAY = '2026-11-02';
const day = (date: string): number => dayNumber(date);

describe('Datumsfunktionen', () => {
  it('rechnet Datum und Tageszahl hin und zurück und kennt den Wochentag (Montag = 0)', () => {
    expect(dateOfDay(day(MONDAY))).toBe(MONDAY);
    expect(weekdayOf(day(MONDAY))).toBe(0);
    expect(weekdayOf(day('2026-11-08'))).toBe(6);
    expect(dayOf('2026-11-03T12:00:00+00:00')).toBe('2026-11-03');
  });

  it('kürzt Uhrzeiten und wandelt lokale Eingaben in Zeitpunkte mit Zeitzone', () => {
    expect(timeInput('18:30:00')).toBe('18:30');
    const iso = fromLocalInput('2026-11-03T18:30');
    expect(iso.endsWith('Z')).toBe(true);
    expect(localInput(iso)).toBe('2026-11-03T18:30');
    expect(fromLocalInput('')).toBe('');
    expect(localInput('kaputt')).toBe('');
  });
});

describe('Anwesenheit', () => {
  it('einmalige Abwesenheit gilt einschließlich Beginn und Ende', () => {
    const rules: AbsenceWire[] = [{ kind: 'once', start: '2026-11-03', end: '2026-11-04' }];
    expect([2, 3, 4, 5].map((n) => isPresent(rules, day(MONDAY) + n - 2))).toEqual([
      true,
      false,
      false,
      true,
    ]);
  });

  it('wöchentliche Abwesenheitstage', () => {
    const rules: AbsenceWire[] = [{ kind: 'weekly_days', weekdays: [5, 6] }];
    expect(isPresent(rules, day('2026-11-06'))).toBe(true);
    expect(isPresent(rules, day('2026-11-07'))).toBe(false);
  });

  it('Wochenrhythmus wechselt am Wechseltag, auch vor dem Ankerdatum', () => {
    const rules: AbsenceWire[] = [
      {
        kind: 'week_rhythm',
        present_weeks: [0],
        cycle_weeks: 2,
        change_weekday: 4,
        anchor: '2026-11-06',
      },
    ];
    expect(isPresent(rules, day('2026-11-06'))).toBe(true);
    expect(isPresent(rules, day('2026-11-12'))).toBe(true);
    expect(isPresent(rules, day('2026-11-13'))).toBe(false);
    expect(isPresent(rules, day('2026-10-30'))).toBe(false);
  });

  it('die Vorschau beginnt am Montag und umfasst vier Wochen', () => {
    const rules: AbsenceWire[] = [{ kind: 'weekly_days', weekdays: [0] }];
    const preview = presencePreview(rules, '2026-11-04');
    expect(preview).toHaveLength(28);
    expect(preview.slice(0, 3)).toEqual([false, true, true]);
  });

  it('ohne Regeln und bei unvollständigen Daten ist die Person anwesend', () => {
    expect(isPresent([], day(MONDAY))).toBe(true);
    expect(isPresent([{ kind: 'once', start: '', end: '' }], day(MONDAY))).toBe(true);
  });
});
