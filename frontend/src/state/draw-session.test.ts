import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClient } from '../api/index.ts';
import type { PanelRoundWire, TaskDrawWire } from '../api/index.ts';
import { FakeHass } from '../api/fake-hass.testing.ts';
import { DrawSession } from './draw-session.ts';

const draw = (task: string, winner: string | null): TaskDrawWire => ({
  task_id: task,
  winner_id: winner,
  chance: 0.5,
  segments: winner ? [{ person_id: winner, weight: 1, chance: 1 }] : [],
  exclusions: [],
});

function round(results: TaskDrawWire[], pending: string[]): PanelRoundWire {
  return {
    id: 'r1',
    schedule_id: 's1',
    expires_at: '2026-11-03T13:00:00+00:00',
    results,
    pending_task_ids: pending,
  };
}

let hass: FakeHass;
let session: DrawSession;

beforeEach(() => {
  hass = new FakeHass();
  session = new DrawSession(new ApiClient(hass));
});

describe('DrawSession', () => {
  it('führt Aufgabe für Aufgabe durch die Runde und schließt sie ab', async () => {
    const listener = vi.fn();
    session.listen(listener);
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin', {
      result: draw('t1', 'p1'),
      panel_round: round([], []),
    });
    await session.begin('s1');
    expect(session.state).toMatchObject({ phase: 'ready', roundId: 'r1', taskIds: ['t1', 't2'] });

    await session.spin();
    expect(session.state).toMatchObject({ phase: 'spinning', current: { task_id: 't1' } });
    session.landed();
    expect(session.state.phase).toBe('revealed');

    await session.next();
    expect(session.state).toMatchObject({ phase: 'ready', current: undefined });

    hass.replies.set('task_wheel/draw/spin', {
      result: draw('t2', null),
      panel_round: round([], []),
    });
    await session.spin();
    session.landed();
    await session.next();
    expect(session.state.phase).toBe('done');
    expect(hass.calls.at(-1)).toBe('task_wheel/draw/commit');
    expect(hass.messages.at(-1)).toMatchObject({ panel_round_id: 'r1' });
    expect(listener).toHaveBeenCalled();
  });

  it('zieht den Rest ohne Animation und schließt die Runde ab', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [draw('t1', 'p1'), draw('t2', 'p2')],
      panel_round: round([], []),
    });
    await session.begin('s1');
    await session.drawRest();
    expect(session.state.phase).toBe('done');
    expect(session.state.results).toHaveLength(2);
  });

  it('schließt eine Runde ohne fällige Aufgaben sofort ab', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], []));
    await session.begin('s1');
    expect(session.state).toMatchObject({ phase: 'done', results: [] });
  });

  it('setzt eine offene Runde mit ihren bisherigen Ergebnissen fort', () => {
    session.resume(round([draw('t1', 'p1')], ['t2']));
    expect(session.state).toMatchObject({ phase: 'ready', taskIds: ['t1', 't2'] });
    expect(session.state.results).toHaveLength(1);
  });

  it('meldet Fehler der API mit ihrem Code und erlaubt danach einen neuen Anlauf', async () => {
    hass.replies.set('task_wheel/draw/begin', Object.assign(new Error('x'), { code: 'not_found' }));
    await session.begin('s1');
    expect(session.state).toMatchObject({ phase: 'error', errorCode: 'not_found' });
    hass.replies.set('task_wheel/draw/begin', new Error('ohne Code'));
    await session.begin('s1');
    expect(session.state.errorCode).toBe('unknown');
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    await session.begin('s1');
    expect(session.state.phase).toBe('ready');
  });

  it('verwirft die offene Runde beim Neustart, eine abgeschlossene nicht', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    await session.begin('s1');
    await session.restart();
    expect(session.state.phase).toBe('choose');
    expect(hass.calls.at(-1)).toBe('task_wheel/draw/cancel');

    hass.replies.set('task_wheel/draw/begin', round([], []));
    await session.begin('s1');
    hass.calls.length = 0;
    await session.restart();
    expect(hass.calls).toEqual([]);
  });

  it('ignoriert Aktionen außerhalb ihrer Phase', async () => {
    await session.spin();
    await session.next();
    await session.drawRest();
    session.landed();
    expect(session.state.phase).toBe('choose');
    expect(hass.calls).toEqual([]);
    session.resume(round([], ['t1']));
    session.resume(round([], ['t2']));
    expect(session.state.taskIds).toEqual(['t1']);
    await session.begin('s1');
    expect(hass.calls).toEqual([]);
  });

  it('hört auf, Zuhörer zu benachrichtigen, wenn sie sich abmelden', () => {
    const listener = vi.fn();
    session.listen(listener)();
    session.resume(round([], ['t1']));
    expect(listener).not.toHaveBeenCalled();
  });
});
