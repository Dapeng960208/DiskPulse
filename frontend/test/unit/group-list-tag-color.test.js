import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('group list tag colors', () => {
  it('uses visible violet theme tokens for informational tags', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/pages/group/GroupListPage.vue'), 'utf8');
    const variables = readFileSync(resolve(process.cwd(), 'src/styles/variables.scss'), 'utf8');

    expect([...source.matchAll(/class="group-list__info-tag"/g)]).toHaveLength(3);
    expect(source).toContain('--el-tag-bg-color: var(--tag-info-bg)');
    expect(source).toContain('--el-tag-border-color: var(--tag-info-border)');
    expect(source).toContain('--el-tag-text-color: var(--tag-info-color)');
    expect(variables).toContain('--tag-info-bg: #F5F3FF');
    expect(variables).toContain('--tag-info-border: #C4B5FD');
    expect(variables).toContain('--tag-info-color: #7C3AED');
  });
});
