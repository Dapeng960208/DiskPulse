import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'));

describe('frontend dependency security contract', () => {
  it('keeps the package manager out of runtime dependencies and exposes the high-risk audit gate', () => {
    expect(packageJson.dependencies).not.toHaveProperty('pnpm');
    expect(packageJson.packageManager).toMatch(/^pnpm@/);
    expect(packageJson.scripts['audit:high']).toBe(
      'pnpm audit --registry=https://registry.npmjs.org --audit-level high',
    );
  });
});
