import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const incidentPage = 'src/pages/incident/IncidentCenterPage.vue';
const auditPage = 'src/pages/admin/audit/AuditEventListPage.vue';

function sourceFor(file) {
  return readFileSync(file, 'utf8');
}

describe('事件中心和统一操作审计列表布局', () => {
  it('removes page headings and uses the shared query form without custom search actions', () => {
    for (const page of [incidentPage, auditPage]) {
      const source = sourceFor(page);

      expect(source).toContain('<QueryForm');
      expect(source).not.toContain('class="page-heading"');
      expect(source).not.toContain('<header');
    }

    expect(sourceFor(incidentPage)).not.toContain('<template #actions>');
  });

  it('uses the shared data table and pagination contract for event-center results', () => {
    const source = sourceFor(incidentPage);

    expect(source).toContain("import DataTable from '@/components/data/DataTable.vue';");
    expect(source).toContain('<DataTable');
    expect(source).toContain(':pagination="{ page: queryParams.page, pageSize: queryParams.size, total, pageSizes: [20, 50, 100], hideOnSinglePage: true, showJumper: true }"');
    expect(source).toContain('.incident-center-page { display: flex; flex-direction: column; gap: var(--spacing-md); }');
    expect(source).not.toContain('<ElCard');
    expect(source).not.toContain('<ElPagination');
    expect(source).not.toMatch(/<ElTable\s/);
  });

  it('keeps the unified audit filter bar compact with the same layout contract', () => {
    const source = sourceFor(auditPage);

    expect(source).toContain('.audit-event-list-page { display: flex; flex-direction: column; gap: var(--spacing-md); }');
  });
});
