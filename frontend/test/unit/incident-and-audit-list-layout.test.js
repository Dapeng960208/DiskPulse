import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const incidentPage = 'src/pages/incident/IncidentCenterPage.vue';
const auditDetailPage = 'src/pages/admin/audit/AuditEventDetailPage.vue';
const auditPage = 'src/pages/admin/audit/AuditEventListPage.vue';
const auditDrawer = 'src/pages/admin/audit/components/AuditEventDetailDrawer.vue';
const projectAuditTab = 'src/pages/project/components/ProjectAuditTab.vue';

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

  it('opens complete audit details in a right-side drawer instead of navigating away', () => {
    const listSource = sourceFor(auditPage);
    const drawerSource = sourceFor(auditDrawer);

    expect(listSource).toContain("import AuditEventDetailDrawer from './components/AuditEventDetailDrawer.vue';");
    expect(listSource).toContain("import { useRouter } from 'vue-router';");
    expect(listSource).not.toContain('router.push(`/admin/audit-events/${event.id}`)');
    expect(listSource).toContain('<AuditEventDetailDrawer');
    expect(drawerSource).toContain('<ElDrawer');
    expect(drawerSource).toContain('direction="rtl"');
    expect(drawerSource).toContain('变更前摘要');
    expect(drawerSource).toContain('变更后摘要');
    expect(drawerSource).toContain('附加元数据');
  });
  it('provides gated audit-analysis handoffs that pass only ids or filters to AI chat', () => {
    const listSource = sourceFor(auditPage);
    const drawerSource = sourceFor(auditDrawer);
    const detailSource = sourceFor(auditDetailPage);
    const projectSource = sourceFor(projectAuditTab);

    expect(listSource).toContain('AI 研判当前筛选');
    expect(listSource).toContain('canAnalyzeCurrentFilters');
    expect(listSource).toContain('audit_project_id');
    expect(listSource).toContain('audit_start_time');
    expect(listSource).toContain("name: 'AIChat'");
    expect(drawerSource).toContain("defineEmits(['update:modelValue', 'analyze'])");
    expect(drawerSource).toContain('AI 研判');
    expect(detailSource).toContain('AI 研判');
    expect(detailSource).toContain('audit_event_id');
    expect(projectSource).toContain('AI 研判本项目审计');
    expect(projectSource).toContain('audit_project_id');
  });
});
