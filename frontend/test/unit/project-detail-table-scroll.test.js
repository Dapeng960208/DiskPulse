import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('project detail table scrolling', () => {
  it('uses a constrained table region for every paged project-detail tab', () => {
    const page = source('src/pages/project/ProjectDetailPage.vue');

    expect(page.match(/class="project-detail-page__table-tab"/g) || []).toHaveLength(4);
    expect(page).toMatch(/:deep\(.project-detail-page__tabs .project-detail-page__table-tab\) \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);

    for (const tab of [
      'src/pages/project/components/ProjectGroupsTab.vue',
      'src/pages/project/components/ProjectUsagesTab.vue',
      'src/pages/project/components/ProjectMembersTab.vue',
      'src/pages/project/components/ProjectAuditTab.vue',
    ]) {
      expect(source(tab)).toMatch(/display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    }
  });

  it('keeps the pager outside a vertically scrollable table wrapper', () => {
    const dataTable = source('src/components/data/DataTable.vue');

    expect(dataTable).toMatch(/\.table-wrapper \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  overflow: auto;/);
    expect(dataTable).not.toContain('overflow: auto hidden;');
  });
});
