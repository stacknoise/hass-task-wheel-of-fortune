import { describe, expect, it } from 'vitest';

import {
  formatDate,
  formatDateTime,
  formatNumber,
  formatPercent,
  formatShortDate,
} from './format.ts';

describe('Formatierung', () => {
  it('formatiert nach Sprache, bei leerer Sprache englisch', () => {
    expect(formatDate('2026-11-03T12:00:00Z', 'de')).toBe('03.11.2026');
    expect(formatDate('2026-11-03T12:00:00Z', '')).toBe('Nov 3, 2026');
    expect(formatShortDate('2026-11-03T12:00:00Z', 'de')).toBe('3.11.');
    expect(formatDateTime('2026-11-03T12:00:00Z', 'de')).toContain('03.11.2026');
  });

  it('lässt unlesbare Zeiten unverändert', () => {
    expect(formatDateTime('gestern', 'de')).toBe('gestern');
  });

  it('formatiert Anteile und Zahlen', () => {
    expect(formatPercent(0.756, 'en')).toBe('76%');
    expect(formatNumber(0.8333, 'de')).toBe('0,83');
  });
});
