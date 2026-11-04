/**
 * Farben außerhalb der Home-Assistant-Themes: Paletten der Animationen. Gemeinsam genutzte Farben
 * stehen als Tokens in `tokens.ts`. Farbwerte gehören nur in `constants/` (ESLint prüft das).
 */

/** Abdunkelung hinter modalen Fenstern. */
export const COLOR_SCRIM = 'rgb(0 0 0 / 50%)';

/** Oscar-Verleihung: Vorhang, Kuvert, Karte. */
export const OSCAR_COLORS = {
  curtain: '#7a1626',
  stripeDark: '#6d1220',
  stripeLight: '#b3263b',
  paperBorder: '#bda76d',
  paper: '#e7d9b8',
  paperLight: '#f1e6c6',
  card: '#fffaf0',
  bronze: '#8a6d00',
  litGlow: 'rgb(255 236 170 / 70%)',
  winnerGlow: 'rgb(245 197 66 / 60%)',
} as const;

/** Eilmeldung: Zeitungspapier, Druckerschwärze, Stempel. */
export const NEWS_COLORS = {
  paper: '#f6f1e3',
  rule: '#d9d2bd',
  muted: '#5a616b',
  stamp: '#d32f2f',
  shadow: 'rgb(0 0 0 / 35%)',
} as const;

/** Rubbellos: Goldverlauf der Karte. */
export const SCRATCH_COLORS = {
  goldLight: '#fff6d6',
  goldDark: '#ffe08a',
} as const;

/** Scheinwerfer: Leuchten der Gewinnerkachel. */
export const SPOTLIGHT_COLORS = {
  whiteGlow: 'rgb(255 255 255 / 55%)',
} as const;
