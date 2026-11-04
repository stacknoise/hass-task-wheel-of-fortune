import { defineConfig } from 'vitest/config';

const OUT_DIR = '../custom_components/task_wheel/frontend/dist';
const ENTRY = 'src/task-wheel-panel.ts';
const ENTRY_FILE_NAME = 'task-wheel-panel.[hash].js';

export default defineConfig({
  build: {
    outDir: OUT_DIR,
    emptyOutDir: true,
    target: 'es2022',
    lib: { entry: ENTRY, formats: ['es'] },
    rolldownOptions: { output: { entryFileNames: ENTRY_FILE_NAME } },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    setupFiles: ['src/test-setup.testing.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.test.ts', 'src/**/*.testing.ts'],
      thresholds: { lines: 85, functions: 85, branches: 85, statements: 85 },
    },
  },
});
