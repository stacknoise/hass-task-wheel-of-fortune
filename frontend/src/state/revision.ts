import type { Snapshot } from '../api/index.ts';
import { modelsOf } from '../api/index.ts';

const PART_SEPARATOR = ':';
const ITEM_SEPARATOR = '|';

/**
 * Kennzeichen des Stands der Zuteilungen: ändert sich bei jeder neuen Auslosung, jedem Statuswechsel
 * (erledigt, verpasst, unerledigt), jedem Tausch und jeder gelöschten Auslosung.
 */
export function assignmentRevision(snapshot: Snapshot): string {
  const assignments = modelsOf(snapshot, 'assignments').map((item) =>
    [item.id, item.status, item.person_id].join(PART_SEPARATOR),
  );
  const rounds = modelsOf(snapshot, 'rounds').map((item) =>
    [item.id, item.done, item.total].join(PART_SEPARATOR),
  );
  return [...assignments, ...rounds].join(ITEM_SEPARATOR);
}

/** Merkt sich den zuletzt gesehenen Stand und meldet, ob sich die Zuteilungen seither geändert haben. */
export class RevisionTracker {
  #last: string | undefined;

  /** Wahr, wenn sich der Stand seit dem letzten Aufruf geändert hat; der erste Aufruf merkt ihn sich nur. */
  advance(snapshot: Snapshot | undefined): boolean {
    if (!snapshot) {
      return false;
    }
    const revision = assignmentRevision(snapshot);
    const changed = this.#last !== undefined && this.#last !== revision;
    this.#last = revision;
    return changed;
  }
}
