import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8'));
const coverageWorkflow = readFileSync(
  resolve(process.cwd(), '..', '.github', 'workflows', 'coverage-ci.yml'),
  'utf8',
);

describe('frontend dependency security contract', () => {
  it('keeps the package manager out of runtime dependencies and exposes the high-risk audit gate', () => {
    expect(packageJson.dependencies).not.toHaveProperty('pnpm');
    expect(packageJson.packageManager).toMatch(/^pnpm@/);
    expect(packageJson.scripts['audit:high']).toBe(
      'pnpm audit --registry=https://registry.npmjs.org --audit-level high',
    );
  });

  it('uses the declared pnpm lockfile and commands in coverage CI', () => {
    expect(coverageWorkflow).toContain('uses: pnpm/action-setup@v4');
    expect(coverageWorkflow).toContain('cache: pnpm');
    expect(coverageWorkflow).toContain('cache-dependency-path: frontend/pnpm-lock.yaml');
    expect(coverageWorkflow).toContain('run: pnpm install --frozen-lockfile');
    expect(coverageWorkflow).toContain('run: pnpm run test:coverage');
    expect(coverageWorkflow).not.toContain('npm ci');
  });
});
