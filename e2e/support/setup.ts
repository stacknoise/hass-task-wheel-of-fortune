import type { FullConfig } from '@playwright/test';

import { prepare } from './ha.ts';

export default async function setup(config: FullConfig): Promise<void> {
  const base = String(config.projects[0]?.use.baseURL);
  await prepare(base);
}
