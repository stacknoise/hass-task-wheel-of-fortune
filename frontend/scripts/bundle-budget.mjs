// Prüft die gzip-Größe des Panel-Bundles gegen das Budget (siehe docs/CODE_DOKU.md §1.1).
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { gzipSync } from 'node:zlib';

const DIST_DIR = new URL('../../custom_components/task_wheel/frontend/dist/', import.meta.url);
const BUDGET_KB = 120;
const BYTES_PER_KB = 1024;
const EXIT_FAIL = 1;

const files = readdirSync(DIST_DIR).filter((name) => name.endsWith('.js'));
const totalBytes = files.reduce(
  (sum, name) => sum + gzipSync(readFileSync(join(DIST_DIR.pathname, name))).length,
  0,
);
const totalKb = totalBytes / BYTES_PER_KB;
console.log(`Bundle gzip: ${totalKb.toFixed(1)} kB (Budget ${BUDGET_KB} kB)`);
if (totalKb > BUDGET_KB) {
  console.error('Bundle-Budget überschritten.');
  process.exit(EXIT_FAIL);
}
