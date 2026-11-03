import { describe, expect, it } from 'vitest';

import type { Snapshot, WireObject } from '../api/index.ts';
import { RevisionTracker, assignmentRevision } from './revision.ts';

const assignment = (patch: Record<string, unknown> = {}): WireObject => ({
  id: 'a1',
  status: 'open',
  person_id: 'p1',
  ...patch,
});
const round = (patch: Record<string, unknown> = {}): WireObject => ({
  id: 'r1',
  done: 0,
  total: 2,
  ...patch,
});
const snapshot = (assignments: WireObject[], rounds: WireObject[] = [round()]): Snapshot =>
  ({
    persons: [],
    tasks: [],
    schedules: [],
    assignments,
    rounds,
    settings: {},
  }) as unknown as Snapshot;

describe('RevisionTracker', () => {
  it('merkt sich den ersten Stand und meldet erst spätere Änderungen', () => {
    const tracker = new RevisionTracker();
    expect(tracker.advance(undefined)).toBe(false);
    expect(tracker.advance(snapshot([assignment()]))).toBe(false);
    expect(tracker.advance(snapshot([assignment()]))).toBe(false);
    expect(tracker.advance(snapshot([]))).toBe(true);
    expect(tracker.advance(snapshot([]))).toBe(false);
  });

  it('ändert das Kennzeichen bei Status, Person und erledigten Zuteilungen einer Auslosung', () => {
    const base = assignmentRevision(snapshot([assignment()]));
    expect(assignmentRevision(snapshot([assignment({ status: 'skipped' })]))).not.toBe(base);
    expect(assignmentRevision(snapshot([assignment({ person_id: 'p2' })]))).not.toBe(base);
    expect(assignmentRevision(snapshot([assignment()], [round({ done: 1 })]))).not.toBe(base);
  });
});
