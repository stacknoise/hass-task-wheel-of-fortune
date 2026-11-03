import {
  EASE_QUADRATIC,
  SLOT_BRAKE_EXPONENT,
  SLOT_CYCLE_HEIGHT,
  SLOT_EDGE_MARGIN,
  SLOT_HALF,
  SLOT_RECOIL,
  SLOT_REEL_HEIGHT,
  SLOT_START_CYCLE,
  SLOT_START_FRACTION,
  SLOT_TARGET_CYCLE,
} from '../constants/index.ts';
import { easeInOut } from './motion.ts';
import type { Share } from './stage-base.ts';

/** Eine Zeile der Walze; `top` und `height` gelten innerhalb eines Umlaufs. */
export interface SlotCell extends Share {
  readonly top: number;
  readonly height: number;
}

/** Legt die Personen untereinander; die Höhe ist die Chance mal Umlaufhöhe. */
export function layoutCells(
  shares: readonly Share[],
  cycleHeight: number = SLOT_CYCLE_HEIGHT,
): readonly SlotCell[] {
  let top = 0;
  return shares.map((share) => {
    const height = share.share * cycleHeight;
    const cell = { ...share, top, height };
    top += height;
    return cell;
  });
}

/** Stand des Streifens (Punkt unter der Gewinnlinie) innerhalb der Zeile `cell`; `fraction` 0..1 von oben. */
export function targetPosition(
  cell: SlotCell,
  fraction: number,
  cycle: number = SLOT_TARGET_CYCLE,
  cycleHeight: number = SLOT_CYCLE_HEIGHT,
): number {
  const inner = Math.min(Math.max(fraction, SLOT_EDGE_MARGIN), 1 - SLOT_EDGE_MARGIN);
  return cycle * cycleHeight + cell.top + inner * cell.height;
}

/** Stand des Streifens vor dem Start (immer im Startumlauf). */
export function startPosition(cycleHeight: number = SLOT_CYCLE_HEIGHT): number {
  return (SLOT_START_CYCLE + SLOT_START_FRACTION) * cycleHeight;
}

/** Derselbe Anblick im Startumlauf: so bleibt vor jedem Lauf genug Weg bis zum Ziel. */
export function rebase(position: number, cycleHeight: number = SLOT_CYCLE_HEIGHT): number {
  const phase = ((position % cycleHeight) + cycleHeight) % cycleHeight;
  return SLOT_START_CYCLE * cycleHeight + phase;
}

/** Index der Zeile unter der Gewinnlinie bei Stand `position`; -1 ohne Zeilen. */
export function cellIndexAt(
  cells: readonly SlotCell[],
  position: number,
  cycleHeight: number = SLOT_CYCLE_HEIGHT,
): number {
  const phase = ((position % cycleHeight) + cycleHeight) % cycleHeight;
  const index = cells.findIndex((cell) => phase < cell.top + cell.height);
  return index < 0 ? cells.length - 1 : index;
}

/** Verschiebung des Streifens, damit `position` in der Mitte des Fensters liegt. */
export function stripOffset(position: number, windowHeight: number = SLOT_REEL_HEIGHT): number {
  return windowHeight * SLOT_HALF - position;
}

/** Position beim kurzen Zurückziehen vor dem Lauf; `progress` 0..1. */
export function recoilPosition(from: number, progress: number): number {
  return from - SLOT_RECOIL * (1 - (1 - progress) ** EASE_QUADRATIC);
}

/** Weicher Anlauf, langes Abbremsen: Anteil des Wegs (0..1) nach Fortschritt `progress` der Zeit. */
export function brakeProgress(progress: number): number {
  return easeInOut(1 - (1 - progress) ** SLOT_BRAKE_EXPONENT);
}
