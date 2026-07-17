import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const readSource = (path) => readFileSync(path, 'utf8');

describe('logo color sidebar treatment', () => {
  it('uses dedicated logo-derived tokens for the sidebar and its menu states', () => {
    const variables = readSource('src/styles/variables.scss');
    const appLayout = readSource('src/layouts/AppLayout.vue');
    const routeMenu = readSource('src/layouts/components/RouteMenu.vue');

    expect(variables).toContain('--aside-bg: #F4FBE1');
    expect(variables).toContain('--aside-active-bg: #E3F5A7');
    expect(variables).toContain('--aside-accent: #5D7A18');
    expect(variables).toMatch(/html\.dark\s*\{[\s\S]*--aside-bg: #25320F/);
    expect(appLayout).toContain('background: var(--aside-bg)');
    expect(routeMenu).toContain('background: var(--aside-bg)');
    expect(routeMenu).toContain('background: var(--aside-active-bg)');
    expect(routeMenu).toContain('color: var(--aside-accent)');
  });
});
