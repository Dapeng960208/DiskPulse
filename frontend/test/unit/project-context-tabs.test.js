import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('project detail information architecture', () => {
  it('keeps project resources inside the selected project context', () => {
    const page = source('src/pages/project/ProjectDetailPage.vue');

    expect(page).toContain('ProjectDiskUsage');
    expect(page).toContain('ProjectUsagesTab');
    expect(page).toContain('label="容量概览"');
    expect(page).toContain('label="项目组"');
    expect(page).toContain('label="用户目录"');
    expect(page).toContain('label="成员与权限"');
    expect(page).toContain(':attribute-id="projectId"');
    expect(page).toContain(':project-id="projectId"');
  });

  it('loads only the selected project user directories and links to their details', () => {
    const tab = source('src/pages/project/components/ProjectUsagesTab.vue');

    expect(tab).toContain('project_id: props.projectId');
    expect(tab).toContain("name: 'UsagesDetail'");
    expect(tab).toContain('<DataTable');
    expect(tab).toContain('<AccessibleResourceLink');
  });
});
