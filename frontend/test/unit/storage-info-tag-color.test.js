import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const softLimitContracts = [
  ['src/pages/group/GroupListPage.vue', 2],
  ['src/pages/usage/UsageListPage.vue', 2],
  ['src/pages/admin/qtree/QtreeListPage.vue', 2],
  ['src/pages/admin/volume/VolumeListPage.vue', 2],
];

const storageTypeContracts = [
  'src/pages/group/GroupListPage.vue',
  'src/pages/usage/UsageListPage.vue',
  'src/pages/project/components/ProjectGroupsTab.vue',
  'src/pages/project/components/ProjectTable.vue',
  'src/pages/admin/aggregate/AggregateListPage.vue',
  'src/pages/admin/volume/VolumeListPage.vue',
  'src/pages/admin/qtree/QtreeListPage.vue',
  'src/pages/admin/storage-cluster/StorageClusterListPage.vue',
];

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('storage information tag colors', () => {
  it('uses slate info tokens for native info controls while keeping charts cyan', () => {
    const variables = source('src/styles/variables.scss');

    expect(variables).toContain('--info-color: #64748B;');
    expect(variables).toContain('--info-bg: #F1F5F9;');
    expect(variables).toContain('--chart-color-info: #06B6D4;');
    expect(variables).not.toContain('--tag-info-color:');
    expect(source('src/styles/style.scss')).not.toContain('.storage-info-tag');
  });

  it('keeps selectable relationship tags on the native gray info type', () => {
    expect(source('src/components/form/GroupSelect.vue')).toContain('tag-type="info"');
    expect(source('src/components/form/QtreeSelect.vue')).toContain('tag-type="info"');
  });

  it('uses semantic tag types for storage types and missing soft limits', () => {
    for (const [path, expectedCount] of softLimitContracts) {
      const page = source(path);
      expect(page, path).not.toContain('storage-info-tag');
      expect([...page.matchAll(/type="warning">无软限额/g)], path)
        .toHaveLength(expectedCount);
    }

    for (const path of storageTypeContracts) {
      const page = source(path);
      expect(page, path).not.toContain('storage-info-tag');
      expect(page, path).toContain('<StorageTypeTag');
    }

    expect(source('src/components/data/StorageTypeTag.vue')).toContain('type="success"');
  });
});
