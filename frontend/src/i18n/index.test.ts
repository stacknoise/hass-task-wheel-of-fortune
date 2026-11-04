import { describe, expect, it } from 'vitest';

import { translate } from './index.ts';

describe('translate', () => {
  it('liefert deutsche Texte', () => {
    expect(translate('panel.title', 'de')).toBe('Aufgaben-Glücksrad');
  });

  it('fällt auf die Standardsprache zurück', () => {
    expect(translate('panel.title', 'xx')).toBe('Task Wheel of Fortune');
  });
});

describe('translate mit Platzhaltern', () => {
  it('ersetzt benannte Platzhalter und lässt unbekannte stehen', () => {
    expect(translate('overview.openCount', 'de', { count: 3 })).toBe('3 offen');
    expect(translate('overview.openCount', 'de', {})).toBe('{count} offen');
  });
});
