import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

function source(path) {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

describe('progressive filter page contracts', () => {
  it('groups project-group filters into primary and advanced sections with removable chips', () => {
    const groupPage = source('src/pages/group/GroupListPage.vue');
    const [primary, advanced = ''] = groupPage.split('<template #advanced>');

    expect(groupPage).toContain(':advanced-count="activeAdvancedCount"');
    expect(primary).toMatch(/项目组名[\s\S]*关联项目[\s\S]*存储集群/);
    expect(advanced).toMatch(/项目组标签[\s\S]*关联存储空间[\s\S]*关联Qtree（NetApp）/);
    expect(groupPage).toContain('<template #active-filters>');
    expect(groupPage).toContain('@close="removeGroupTagFilter"');
    expect(groupPage).toContain('@close="removeVolumeFilter"');
    expect(groupPage).toContain('@close="removeQtreeFilter"');
  });

  it('groups usage filters into primary and advanced sections with dependent cleanup', () => {
    const usagePage = source('src/pages/usage/UsageListPage.vue');
    const [primary, advanced = ''] = usagePage.split('<template #advanced>');

    expect(usagePage).toContain(':advanced-count="activeAdvancedCount"');
    expect(primary).toMatch(/研发用户名[\s\S]*项目[\s\S]*存储集群/);
    expect(advanced).toMatch(/项目组标签[\s\S]*Linux目录[\s\S]*项目组/);
    expect(usagePage).toContain('<template #active-filters>');
    expect(usagePage).toContain('@close="removeGroupTagFilter"');
    expect(usagePage).toContain('@close="removeLinuxPathFilter"');
    expect(usagePage).toContain('@close="removeGroupFilter"');
    expect(usagePage).toContain('selectedGroupLabel.value = null');
  });
});
