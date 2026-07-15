import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('group list tag colors', () => {
  it('uses neutral theme tokens for informational tags', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/pages/group/GroupListPage.vue'), 'utf8');

    expect([...source.matchAll(/class="group-list__info-tag"/g)]).toHaveLength(3);
    expect(source).toContain('--el-tag-bg-color: var(--bg-tertiary)');
    expect(source).toContain('--el-tag-border-color: var(--border-dark)');
    expect(source).toContain('--el-tag-text-color: var(--text-secondary)');
  });
});
