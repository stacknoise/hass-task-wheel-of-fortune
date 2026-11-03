/** Typisierter Zugriff auf die Sammlungen des Snapshots (die Leitung liefert `WireObject`). */

import type { PersonWire, ScheduleWire, TaskWire } from './config-types.ts';
import type { Snapshot } from './types.ts';

export function personsOf(snapshot: Snapshot): readonly PersonWire[] {
  return snapshot.persons as unknown as readonly PersonWire[];
}

export function tasksOf(snapshot: Snapshot): readonly TaskWire[] {
  return snapshot.tasks as unknown as readonly TaskWire[];
}

export function schedulesOf(snapshot: Snapshot): readonly ScheduleWire[] {
  return snapshot.schedules as unknown as readonly ScheduleWire[];
}
