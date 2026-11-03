import js from '@eslint/js';
import boundaries from 'eslint-plugin-boundaries';
import tseslint from 'typescript-eslint';

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
    files: ['**/*.test.ts'],
    rules: { 'no-magic-numbers': 'off' },
  },
  {
    files: ['**/*.{js,mjs}'],
    extends: [tseslint.configs.disableTypeChecked],
    languageOptions: { globals: { URL: 'readonly', console: 'readonly', process: 'readonly' } },
  },
);
