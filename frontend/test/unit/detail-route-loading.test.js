import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const detailPages = [
  'src/pages/group/GroupDetailPage.vue',
  'src/pages/usage/UsageDetailPage.vue',
  'src/pages/common/RealTimePage.vue',
];

describe('detail route loading dependencies', () => {
  it.each(detailPages)('%s does not request unused Element Plus row or column styles', (path) => {
    const source = readFileSync(resolve(process.cwd(), path), 'utf8');
    const elementPlusImport = source.match(/import\s+\{([^}]+)\}\s+from 'element-plus';/);

    const importedComponents = elementPlusImport?.[1].split(',').map((name) => name.trim());

    expect(importedComponents).not.toContain('ElRow');
    expect(importedComponents).not.toContain('ElCol');
  });
});
