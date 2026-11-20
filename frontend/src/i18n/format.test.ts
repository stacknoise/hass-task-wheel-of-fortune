import { describe, expect, it, vi } from 'vitest';

import { formatDateTime, formatNumber, formatPercent, formatShortDate } from './format.ts';

describe('Formatierung', () => {
  it('formatiert nach Sprache, bei leerer Sprache englisch', () => {
    expect(formatDateTime('2026-11-03T12:00:00Z', '')).toContain('Nov 3, 2026');
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

  it('baut jeden Formatierer pro Sprache nur einmal', () => {
    const construct = vi.spyOn(Intl, 'NumberFormat');
    formatNumber(1, 'it');
    formatNumber(2, 'it');
    formatPercent(0.5, 'it');
    formatPercent(0.25, 'it');
    expect(construct).toHaveBeenCalledTimes(2);
    construct.mockRestore();
  });
});
