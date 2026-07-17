import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const readSource = (path) => readFileSync(path, 'utf8');

describe('logo color sidebar treatment', () => {
  it('applies the logo-derived color only to navigation icons', () => {
    const variables = readSource('src/styles/variables.scss');
    const routeMenu = readSource('src/layouts/components/RouteMenu.vue');

    expect(variables).toContain('--sidebar-icon-color: #76A51D');
    expect(variables).toMatch(/html\.dark\s*\{[\s\S]*--sidebar-icon-color: #B0E237/);
    expect(routeMenu).toContain('color: var(--sidebar-icon-color)');
    expect(routeMenu).toMatch(/\.route-menu[\s\S]*\.el-menu-item > i/);
    expect(routeMenu).toMatch(/\.el-sub-menu__title > i/);
    expect(routeMenu).not.toContain('background: var(--aside-bg)');
  });
});
