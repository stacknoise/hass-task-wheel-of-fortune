import { describe, expect, it } from 'vitest';

import { ApiClient } from './client.ts';
import { FakeHass } from './fake-hass.testing.ts';

describe('ApiClient: zwischengespeicherte Listen', () => {
  it('liefert dieselbe Raumliste, solange hass dieselben Räume meldet', () => {
    const hass = new FakeHass();
    const client = new ApiClient(hass);
    const first = client.areas();
    expect(first.map((area) => area.label)).toEqual(['Bad', 'Küche']);
    expect(client.areas()).toBe(first);

    // Eine Zustandsänderung irgendeiner Entität ersetzt hass, nicht aber die Räume.
    client.useHass(Object.create(hass, { states: { value: {} } }) as FakeHass);
    expect(client.areas()).toBe(first);

    client.useHass(
      Object.create(hass, { areas: { value: { flur: { name: 'Flur' } } } }) as FakeHass,
    );
    expect(client.areas().map((area) => area.id)).toEqual(['flur']);
  });

  it('berechnet die Benachrichtigungsziele neu, wenn sich Zustände oder Dienste ändern', () => {
    const hass = new FakeHass();
    const client = new ApiClient(hass);
    const first = client.notifyTargets();
    expect(first.map((target) => target.id)).toEqual([
      'notify.handy_anna',
      'notify.kueche',
      'notify.mobile_app_ben',
    ]);
    expect(client.notifyTargets()).toBe(first);

    client.useHass(
      Object.create(hass, {
        states: { value: { 'notify.neu': { attributes: { friendly_name: 'Neu' } } } },
      }) as FakeHass,
    );
    expect(client.notifyTargets()).not.toBe(first);
    expect(client.notifyTargets().some((target) => target.id === 'notify.neu')).toBe(true);
  });
});
