import { describe, expect, it } from 'vitest';

import { ApiClient } from './client.ts';
import { failureFor, parseFailure } from './errors.ts';
import { FakeHass } from './fake-hass.testing.ts';

describe('Fehler der API', () => {
  it('zerlegt Prüffehler in Schlüssel und Feldpfad', () => {
    expect(
      parseFailure({ code: 'out_of_range', message: 'trigger.weekdays: out_of_range' }),
    ).toEqual({
      code: 'out_of_range',
      field: 'trigger.weekdays',
    });
    expect(parseFailure({ code: 'in_use', message: 'in_use' })).toEqual({
      code: 'in_use',
      field: '',
    });
    expect(parseFailure({ code: 'x' })).toEqual({ code: 'x', field: '' });
    expect(parseFailure(new Error('offline'))).toEqual({ code: 'unknown', field: '' });
    expect(parseFailure(undefined)).toEqual({ code: 'unknown', field: '' });
  });

  it('ordnet Fehler Feldern und deren Unterpfaden zu', () => {
    const failure = { code: 'required', field: 'trigger.time' };
    expect(failureFor(failure, 'trigger')).toBe('required');
    expect(failureFor(failure, 'trigger.time')).toBe('required');
    expect(failureFor(failure, 'name')).toBeUndefined();
    expect(failureFor(failure, 'trigger.t')).toBeUndefined();
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

  it('löscht über die Kennung', async () => {
    const hass = new FakeHass();
    await new ApiClient(hass).deleteConfig('schedule', 's1');
    expect(hass.messages).toEqual([{ type: 'task_wheel/schedule/delete', schedule_id: 's1' }]);
  });
});
