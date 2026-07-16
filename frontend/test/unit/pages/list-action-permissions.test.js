import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const readPage = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

function actionColumn(source) {
  const start = source.lastIndexOf('<ElTableColumn');
  return source.slice(start, source.indexOf('</ElTableColumn>', start));
}

describe('role-aware list actions', () => {
  const groupSource = readPage('src/pages/group/GroupListPage.vue');
  const usageSource = readPage('src/pages/usage/UsageListPage.vue');

  it.each([
    ['group', groupSource],
    ['usage', usageSource],
  ])('keeps details direct and gates the more menu for %s', (_, source) => {
    const actions = actionColumn(source);

    expect(actions).toContain('width="132"');
    expect(actions).toContain('class="list-row-actions"');
    expect(actions.indexOf('详情')).toBeLessThan(actions.indexOf('<ElDropdown'));
    expect(actions).toMatch(/<ElDropdown[\s\S]*?v-if="hasRole\('disk-monitor:admin'\)"/);
    expect(actions).toContain('aria-label="更多操作"');
  });

  it('keeps group management actions in the admin menu', () => {
    const actions = actionColumn(groupSource);

    expect(actions).toContain('调整配额');
    expect(actions).toContain('编辑');
    expect(actions).toContain('删除');
    expect(actions).toContain('class="list-row-actions__danger"');
  });

  it('keeps only quota adjustment in the usage admin menu', () => {
    const actions = actionColumn(usageSource);

    expect(actions).toContain('调整配额');
    expect(actions).not.toContain('编辑');
    expect(actions).not.toContain('删除');
  });

  it.each([
    ['添加项目组', groupSource],
    ['新增', usageSource],
  ])('shows %s only to admins', (label, source) => {
    const header = actionColumn(source).match(/<template[\s\S]*?#header[^>]*>([\s\S]*?)<\/template>/)?.[1];

    expect(header).toContain('v-if="hasRole(\'disk-monitor:admin\')"');
    expect(header).toContain(label);
  });
});
