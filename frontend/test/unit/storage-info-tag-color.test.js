import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const sources = [
  ['src/pages/group/GroupListPage.vue', 3],
  ['src/pages/usage/UsageListPage.vue', 3],
  ['src/pages/admin/qtree/QtreeListPage.vue', 2],
  ['src/pages/admin/volume/VolumeListPage.vue', 2],
  ['src/pages/project/ProjectDetailPage.vue', 1],
  ['src/pages/project/components/ProjectTable.vue', 1],
];

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('storage information tag colors', () => {
  it('uses one shared violet style for storage types and missing soft limits', () => {
    for (const [path, expectedCount] of sources) {
      const page = source(path);
      expect([...page.matchAll(/storage-info-tag/g)], path).toHaveLength(expectedCount);
      expect([...page.matchAll(/type="info"/g)], path).toHaveLength(expectedCount);
    }

    const style = source('src/styles/style.scss');
    expect(style).toContain('.storage-info-tag');
    expect(style).toContain('--el-tag-bg-color: var(--tag-info-bg)');
    expect(style).toContain('--el-tag-border-color: var(--tag-info-border)');
    expect(style).toContain('--el-tag-text-color: var(--tag-info-color)');
    expect(source('src/pages/group/GroupListPage.vue')).not.toContain('group-list__info-tag');
  });
});
