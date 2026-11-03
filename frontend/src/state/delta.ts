import type { CollectionDelta, Delta, Snapshot, WireObject } from '../api/index.ts';
import { COLLECTIONS, KEY_ID } from '../constants/index.ts';

/** Wendet die Änderung einer Sammlung an: ersetzt oder ergänzt Objekte nach Kennung, entfernt gelöschte. */
export function applyCollectionDelta(
  items: readonly WireObject[],
  delta: CollectionDelta,
): readonly WireObject[] {
  const byId = new Map(items.map((item) => [item[KEY_ID], item]));
  for (const id of delta.remove) {
    byId.delete(id);
  }
  for (const item of delta.upsert) {
    byId.set(item[KEY_ID], item);
  }
  return [...byId.values()];
}

/** Wendet ein Delta auf den Stand an; unveränderte Sammlungen behalten ihre Identität. */
export function applyDelta(snapshot: Snapshot, delta: Delta): Snapshot {
  const next = { ...snapshot, now: snapshot.now };
  for (const name of COLLECTIONS) {
    const change = delta[name];
    if (change) {
      Object.assign(next, { [name]: applyCollectionDelta(snapshot[name], change) });
    }
  }
  return delta.settings ? { ...next, settings: delta.settings } : next;
}
