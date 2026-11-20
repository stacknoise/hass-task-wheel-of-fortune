import { describe, expect, it } from 'vitest';

import { ApiClient } from './client.ts';
import { failureFor, parseFailure } from './errors.ts';
import { FakeHass } from './fake-hass.testing.ts';

describe('Fehler der API', () => {
  it('zerlegt Prüffehler in Schlüssel und Feldpfad', () => {
    expect(parseFailure({ code: 'out_of_range', message: 'interval.every: out_of_range' })).toEqual(
      {
        code: 'out_of_range',
        field: 'interval.every',
      },
    );
    expect(parseFailure({ code: 'in_use', message: 'in_use' })).toEqual({
      code: 'in_use',
      field: '',
    });
    expect(parseFailure({ code: 'x' })).toEqual({ code: 'x', field: '' });
    expect(parseFailure(new Error('offline'))).toEqual({ code: 'unknown', field: '' });
    expect(parseFailure(undefined)).toEqual({ code: 'unknown', field: '' });
  });

  it('ordnet Fehler Feldern und deren Unterpfaden zu', () => {
    const failure = { code: 'required', field: 'interval.unit' };
    expect(failureFor(failure, 'interval')).toBe('required');
    expect(failureFor(failure, 'interval.unit')).toBe('required');
    expect(failureFor(failure, 'name')).toBeUndefined();
    expect(failureFor(failure, 'interval.u')).toBeUndefined();
    expect(failureFor(undefined, 'name')).toBeUndefined();
  });
});

describe('ApiClient: Konfiguration', () => {
  it('legt an (ohne Kennung) und ändert (mit Kennung)', async () => {
    const hass = new FakeHass();
    const client = new ApiClient(hass);
    await client.saveConfig('person', undefined, { name: 'Anna' });
    await client.saveConfig('task', 't1', { name: 'Müll' });
    expect(hass.messages).toEqual([
      { type: 'task_wheel/person/create', person: { name: 'Anna' } },
      { type: 'task_wheel/task/update', task_id: 't1', task: { name: 'Müll' } },
    ]);
  });

  it('beginnt die Auslosung nur mit dem Zeitplan', async () => {
    const hass = new FakeHass();
    await new ApiClient(hass).beginDraw('s1');
    expect(hass.messages).toEqual([{ type: 'task_wheel/draw/begin', schedule_id: 's1' }]);
  });

  it('lässt die Planung eines Zeitplans im Backend bewerten', async () => {
    const hass = new FakeHass();
    const plan = {
      interval: { unit: 'day', every: 7 },
      run_days: 30,
      entries: [{ task_id: 't1', mode: 'min_count', min_count: 2 }],
    } as const;
    await new ApiClient(hass).planPreview(plan);
    expect(hass.messages).toEqual([{ type: 'task_wheel/schedule/plan_preview', ...plan }]);
  });

  it('löscht über die Kennung', async () => {
    const hass = new FakeHass();
    await new ApiClient(hass).deleteConfig('schedule', 's1');
    expect(hass.messages).toEqual([{ type: 'task_wheel/schedule/delete', schedule_id: 's1' }]);
  });
});
