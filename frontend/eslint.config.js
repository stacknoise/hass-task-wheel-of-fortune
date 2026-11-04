import js from '@eslint/js';
import boundaries from 'eslint-plugin-boundaries';
import tseslint from 'typescript-eslint';

// Hexfarben (#rgb, #rrggbb, #rrggbbaa) und rgb()/rgba()/hsl()/hsla() als Muster für Selektoren.
const COLOR_LITERAL = '#[0-9a-fA-F]{3,8}\\b|\\b(?:rgba?|hsla?)\\(';
const LAYERS = ['views', 'components', 'state', 'api', 'i18n', 'constants'];
// Erlaubte Importrichtung: views -> components -> state/api -> constants/i18n
const ALLOWED = {
  views: ['components', 'state', 'api', 'i18n', 'constants'],
  components: ['state', 'i18n', 'constants'],
  state: ['api', 'constants'],
  api: ['constants'],
  i18n: ['constants'],
  constants: [],
};

export default tseslint.config(
  { ignores: ['node_modules', 'coverage', '../custom_components/task_wheel/frontend/dist'] },
  js.configs.recommended,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    plugins: { boundaries },
    settings: {
      'boundaries/elements': [...LAYERS.map((type) => ({ type, pattern: `src/${type}/**` }))],
      'boundaries/files': [{ category: 'entry', pattern: 'src/*.ts' }],
    },
    rules: {
      'no-magic-numbers': ['error', { ignore: [0, 1, -1], ignoreArrayIndexes: true }],
      'boundaries/dependencies': [
        'error',
        {
          default: 'disallow',
          policies: [
            {
              from: { file: { categories: 'entry' } },
              allow: [
                { to: { element: { types: LAYERS } } },
                { to: { file: { categories: 'entry' } } },
              ],
            },
            ...Object.entries(ALLOWED).map(([from, to]) => ({
              from: { element: { type: from } },
              allow: { to: { element: { types: [from, ...to] } } },
            })),
          ],
        },
      ],
    },
  },
  {
    // Konstanten sind der Ort für Literale
    files: ['src/constants/**/*.ts'],
    rules: { 'no-magic-numbers': 'off' },
  },
  {
    // Farben (Hex, rgb, hsl) gehören als Konstanten nach constants/ oder als Token nach tokens.ts,
    // auch innerhalb der css-Vorlagen, die `no-magic-numbers` nicht prüft.
    files: ['src/**/*.ts'],
    ignores: ['src/constants/**', '**/*.test.ts', '**/*.testing.ts'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector: `TemplateElement[value.raw=/${COLOR_LITERAL}/]`,
          message:
            'Farbwerte gehören nach src/constants (colors.ts, tokens.ts), nicht in die Vorlage.',
        },
        {
          selector: `Literal[value=/^${COLOR_LITERAL}$/]`,
          message: 'Farbwerte gehören nach src/constants (colors.ts, tokens.ts).',
        },
      ],
    },
  },
  {
    files: ['**/*.test.ts', '**/*.testing.ts'],
    rules: { 'no-magic-numbers': 'off' },
  },
  {
    files: ['**/*.{js,mjs}'],
    extends: [tseslint.configs.disableTypeChecked],
    languageOptions: { globals: { URL: 'readonly', console: 'readonly', process: 'readonly' } },
  },
);
