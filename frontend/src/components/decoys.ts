import type { Random } from './spotlight-geometry.ts';

/** Bis zu `count` zufällige Ids ohne `winner`, jede höchstens einmal. */
export function decoysOf(
  ids: readonly string[],
  winner: string,
  count: number,
  random: Random,
): string[] {
  const pool = ids.filter((id) => id !== winner);
  const picked: string[] = [];
  while (picked.length < count && pool.length > 0) {
    const [id] = pool.splice(Math.min(Math.floor(random() * pool.length), pool.length - 1), 1);
    if (id !== undefined) {
      picked.push(id);
    }
  }
  return picked;
}
