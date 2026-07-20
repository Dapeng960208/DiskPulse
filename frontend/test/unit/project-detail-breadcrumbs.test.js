import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('project child detail breadcrumbs', () => {
  it('derives project, project name, and resource-specific detail labels from loaded records', () => {
    const projectDetail = source('src/pages/project/ProjectDetailPage.vue');
    const groupDetail = source('src/pages/group/GroupDetailPage.vue');
    const usageDetail = source('src/pages/usage/UsageDetailPage.vue');

    expect(projectDetail).toContain('setDetailBreadcrumb(route.name');
    expect(groupDetail).toContain('setDetailBreadcrumb(route.name');
    expect(usageDetail).toContain('setDetailBreadcrumb(route.name');
    expect(usageDetail).toContain('用户详情');
    expect(groupDetail).toContain('项目组详情');
  });
});
