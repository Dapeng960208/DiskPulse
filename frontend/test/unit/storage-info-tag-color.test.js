import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const softLimitContracts = [
  ['src/pages/group/GroupListPage.vue', 2],
  ['src/pages/usage/UsageListPage.vue', 2],
  ['src/pages/admin/qtree/QtreeListPage.vue', 2],
  ['src/pages/admin/volume/VolumeListPage.vue', 2],
];

const storageTypeContracts = [
  ['src/pages/group/GroupListPage.vue', 'type="info"'],
  ['src/pages/usage/UsageListPage.vue', 'type="success"'],
  ['src/pages/project/ProjectDetailPage.vue', 'type="info"'],
  ['src/pages/project/components/ProjectTable.vue', 'type="info"'],
];

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('storage information tag colors', () => {
  it('uses semantic tag types for storage types and missing soft limits', () => {
    for (const [path, expectedCount] of softLimitContracts) {
      const page = source(path);
      expect(page, path).not.toContain('storage-info-tag');
      expect([...page.matchAll(/type="warning">无软限额/g)], path)
        .toHaveLength(expectedCount);
    }

    for (const [path, expectedType] of storageTypeContracts) {
      const page = source(path);
      expect(page, path).not.toContain('storage-info-tag');
      expect(page, path).toContain(expectedType);
    }
  });
});
