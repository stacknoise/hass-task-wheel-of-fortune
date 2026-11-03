/** Auslosungs-Animationen: Arten, Bausteine und Standard. Die Ziehung selbst bleibt im Backend. */

export const ANIMATION_KINDS = ['wheel', 'drum', 'slot', 'plinko', 'spotlight'] as const;
export type AnimationKind = (typeof ANIMATION_KINDS)[number];

/** Gilt für Zeitpläne ohne Auswahl (wie im Backend: `DEFAULT_ANIMATIONS`). */
export const DEFAULT_ANIMATIONS: readonly AnimationKind[] = ['wheel'];

export const STAGE_TAG = 'tw-stage';

/** Element je Animationsart; jedes bietet `segments`, `label` und `spinTo(id)`. */
export const STAGE_TAGS: Readonly<Record<AnimationKind, string>> = {
  wheel: 'tw-wheel',
  drum: 'tw-drum',
  slot: 'tw-slot',
  plinko: 'tw-plinko',
  spotlight: 'tw-spotlight',
};

/** Wo der Knopf zum Starten sitzt: in der Mitte der Bühne (Rad) oder darunter. */
export type StartPlacement = 'center' | 'below';
export const START_PLACEMENT: Readonly<Record<AnimationKind, StartPlacement>> = {
  wheel: 'center',
  drum: 'below',
  slot: 'below',
  plinko: 'below',
  spotlight: 'below',
};
