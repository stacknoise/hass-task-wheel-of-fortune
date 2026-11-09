import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClient } from '../api/index.ts';
import type { DrawWindowRequest, PanelRoundWire, TaskDrawWire } from '../api/index.ts';
import { FakeHass } from '../api/fake-hass.testing.ts';
import { DrawSession, canSkip, isIdle, needsConfirmation, shownCount } from './draw-session.ts';

const draw = (task: string, winner: string | null): TaskDrawWire => ({
  task_id: task,
  winner_id: winner,
  chance: 0.5,
  segments: winner ? [{ person_id: winner, weight: 1, chance: 1 }] : [],
  exclusions: [],
});

function round(
  results: TaskDrawWire[],
  pending: string[],
  unplaceable: string[] = [],
): PanelRoundWire {
  return {
    id: 'r1',
    schedule_id: 's1',
    expires_at: '2026-11-03T13:00:00+00:00',
    results,
    pending_task_ids: pending,
    unplaceable_task_ids: unplaceable,
    participant_ids: [],
  };
}

const WINDOW: DrawWindowRequest = {
  starts_at: '2026-11-03T10:00:00+00:00',
  duration: 3,
  duration_unit: 'day',
  replace_next: false,
};

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
    await session.begin('s1', WINDOW);
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

  it('lädt das Rad der nächsten Aufgabe schon vor dem Drehen', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/preview', { result: draw('t1', null) });
    hass.replies.set('task_wheel/draw/spin', {
      result: draw('t1', 'p1'),
      panel_round: round([], []),
    });
    await session.begin('s1', WINDOW);
    expect(session.state.preview?.task_id).toBe('t1');
    await session.spin();
    session.landed();
    hass.replies.set('task_wheel/draw/preview', { result: draw('t2', null) });
    await session.next();
    expect(session.state.preview?.task_id).toBe('t2');
  });

  it('hält die Runde bei nicht vergebbaren Aufgaben an, bis der Benutzer entscheidet', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2'], ['t2']));
    hass.replies.set('task_wheel/draw/spin', {
      result: draw('t1', 'p1'),
      panel_round: round([], ['t2']),
    });
    await session.begin('s1', WINDOW, false);
    expect(session.state).toMatchObject({ phase: 'ready', direct: true, unplaceable: ['t2'] });
    expect(needsConfirmation(session.state)).toBe(true);
    expect(canSkip(session.state)).toBe(false);

    await session.drawRest();
    await session.spin();
    expect(hass.calls).not.toContain('task_wheel/draw/spin_rest');
    expect(hass.calls).not.toContain('task_wheel/draw/spin');

    session.confirmUnplaceable();
    expect(needsConfirmation(session.state)).toBe(false);
    await session.spin();
    expect(session.state.phase).toBe('spinning');
  });

  it('fragt nach dem Austausch erneut, wenn weiter Aufgaben nicht vergebbar sind', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2'], ['t2']));
    hass.replies.set('task_wheel/draw/preview', { result: draw('t1', null) });
    hass.replies.set('task_wheel/draw/replace_task', { panel_round: round([], ['t1', 't3'], []) });
    await session.begin('s1', WINDOW);
    session.confirmUnplaceable();
    await session.replaceTask('t2', 't3');
    expect(session.state).toMatchObject({ unplaceable: [], confirmed: false });
  });

  it('kommt ohne Vorschau aus, wenn sie fehlschlägt', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    hass.replies.set('task_wheel/draw/preview', new Error('x'));
    await session.begin('s1', WINDOW);
    expect(session.state).toMatchObject({ phase: 'ready', preview: undefined });
  });

  it('zieht den Rest ohne Animation und schließt die Runde ab', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    hass.replies.set('task_wheel/draw/spin_rest', {
      results: [draw('t1', 'p1'), draw('t2', 'p2')],
      panel_round: round([], []),
    });
    await session.begin('s1', WINDOW);
    await session.drawRest();
    expect(session.state.phase).toBe('done');
    expect(session.state.results).toHaveLength(2);
  });

  it('schließt eine Runde ohne fällige Aufgaben sofort ab', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], []));
    await session.begin('s1', WINDOW);
    expect(session.state).toMatchObject({ phase: 'done', results: [] });
  });

  it('setzt eine offene Runde mit ihren bisherigen Ergebnissen fort', () => {
    session.resume(round([draw('t1', 'p1')], ['t2']));
    expect(session.state).toMatchObject({ phase: 'ready', taskIds: ['t1', 't2'] });
    expect(session.state.results).toHaveLength(1);
  });

  it('meldet Fehler der API mit ihrem Code und erlaubt danach einen neuen Anlauf', async () => {
    hass.replies.set('task_wheel/draw/begin', Object.assign(new Error('x'), { code: 'not_found' }));
    await session.begin('s1', WINDOW);
    expect(session.state).toMatchObject({ phase: 'error', errorCode: 'not_found' });
    hass.replies.set('task_wheel/draw/begin', new Error('ohne Code'));
    await session.begin('s1', WINDOW);
    expect(session.state.errorCode).toBe('unknown');
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    await session.begin('s1', WINDOW);
    expect(session.state.phase).toBe('ready');
  });

  it('verwirft die offene Runde beim Neustart, eine abgeschlossene nicht', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    await session.begin('s1', WINDOW);
    await session.restart();
    expect(session.state.phase).toBe('choose');
    expect(hass.calls.at(-1)).toBe('task_wheel/draw/cancel');

    hass.replies.set('task_wheel/draw/begin', round([], []));
    await session.begin('s1', WINDOW);
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
    await session.begin('s1', WINDOW);
    expect(hass.calls).toEqual(['task_wheel/draw/preview']);
  });

  it('hört auf, Zuhörer zu benachrichtigen, wenn sie sich abmelden', () => {
    const listener = vi.fn();
    session.listen(listener)();
    session.resume(round([], ['t1']));
    expect(listener).not.toHaveBeenCalled();
  });

  it('verwirft die Antwort einer Anfrage, die einen Neustart überdauert', async () => {
    hass.replies.set('task_wheel/draw/begin', round([], ['t1']));
    await session.begin('s1', WINDOW);
    let answer: (value: unknown) => void = () => undefined;
    hass.replies.set(
      'task_wheel/draw/spin',
      new Promise((resolve) => {
        answer = resolve;
      }),
    );
    const spinning = session.spin();
    expect(session.state.phase).toBe('busy');
    await session.restart();
    answer({ result: draw('t1', 'p1'), panel_round: round([], []) });
    await spinning;
    expect(session.state).toMatchObject({ phase: 'choose', roundId: undefined, results: [] });
  });

  it('beschreibt Leerlauf, gezeigte Ergebnisse und Überspringen als reine Funktionen', async () => {
    expect(isIdle(session.state)).toBe(true);
    hass.replies.set('task_wheel/draw/begin', round([], ['t1', 't2']));
    await session.begin('s1', WINDOW);
    expect(isIdle(session.state)).toBe(false);
    expect(canSkip(session.state)).toBe(true);
    expect(shownCount(session.state)).toBe(0);
    expect(canSkip({ ...session.state, phase: 'busy' })).toBe(false);
    expect(shownCount({ ...session.state, phase: 'spinning', results: [draw('t1', 'p1')] })).toBe(
      0,
    );
  });
});
