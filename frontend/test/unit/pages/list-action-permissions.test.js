import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

const readPage = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

function actionColumn(source) {
  const start = source.lastIndexOf('<ElTableColumn');
  return source.slice(start, source.indexOf('</ElTableColumn>', start));
}

function columnContaining(source, text) {
  const position = source.indexOf(text);
  const start = source.lastIndexOf('<ElTableColumn', position);
  return source.slice(start, source.indexOf('</ElTableColumn>', position));
}

function vueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return vueFiles(path);
    return entry.name.endsWith('.vue') ? [path] : [];
  });
}

describe('role-aware list actions', () => {
  const groupSource = readPage('src/pages/group/GroupListPage.vue');
  const usageSource = readPage('src/pages/usage/UsageListPage.vue');

  it.each([
    ['group', groupSource],
    ['usage', usageSource],
  ])('keeps details direct and gates the more menu for %s', (_, source) => {
    const actions = actionColumn(source);

    expect(actions).toContain('width="132"');
    expect(actions).toContain('class="list-row-actions"');
    expect(actions.indexOf('详情')).toBeLessThan(actions.indexOf('<ElDropdown'));
    if (source === groupSource || source === usageSource) {
      expect(actions).toMatch(/<ElDropdown[\s\S]*?v-if="hasRole\('disk-monitor:admin'\) \|\| canAdjustQuota\(row\)"/);
    }
    expect(actions).toContain('aria-label="更多操作"');
  });

  it('keeps group management actions in the admin menu', () => {
    const actions = actionColumn(groupSource);

    expect(actions).toContain('调整配额');
    expect(actions).toContain('编辑');
    expect(actions).toContain('删除');
    expect(actions).toContain('class="list-row-actions__danger"');
  });

  it('shows group quota adjustment only when the resource capability is granted', () => {
    const actions = actionColumn(groupSource);

    expect(groupSource).toContain('function canAdjustQuota(row)');
    expect(groupSource).toContain('row?.capabilities?.adjust_quota === true');
    expect(actions).toContain('v-if="canAdjustQuota(row)"');
  });

  it('shows user-directory quota adjustment only when the resource capability is granted', () => {
    const actions = actionColumn(usageSource);

    expect(usageSource).toContain('function canAdjustQuota(row)');
    expect(usageSource).toContain('row?.capabilities?.adjust_quota === true');
    expect(actions).toMatch(/v-if="hasRole\('disk-monitor:admin'\) \|\| canAdjustQuota\(row\)"/);
  });

  it('does not render user-directory quota adjustment for an admin without resource capability', () => {
    const actions = actionColumn(usageSource);

    expect(actions).toMatch(/<ElDropdownItem\s+v-if="canAdjustQuota\(row\)"[\s\S]*?>\s*调整配额/);
  });

  it('keeps only quota adjustment in the usage admin menu', () => {
    const actions = actionColumn(usageSource);

    expect(actions).toContain('调整配额');
    expect(actions).not.toContain('编辑');
    expect(actions).not.toContain('删除');
  });

  it.each([
    ['添加项目组', groupSource],
    ['新增', usageSource],
  ])('shows %s only to admins', (label, source) => {
    const header = actionColumn(source).match(/<template[\s\S]*?#header[^>]*>([\s\S]*?)<\/template>/)?.[1];

    expect(header).toContain('v-if="hasRole(\'disk-monitor:admin\')"');
    expect(header).toContain(label);
  });
});

describe('global list row actions', () => {
  const storageSource = readPage('src/pages/admin/storage-cluster/StorageClusterListPage.vue');
  const aiSource = readPage('src/pages/admin/ai/AiCenterPage.vue');

  it.each([
    ['src/components/audit/AuditEventTable.vue', "emit('show-detail', row)"],
    ['src/pages/usage/UsageListPage.vue', 'storageUsageFormDialogRef.edit()'],
    ['src/pages/group-tag/GroupTagListPage.vue', 'dialogRef.edit()'],
    ['src/pages/group/GroupListPage.vue', 'groupFormDialogRef.edit()'],
    ['src/pages/project/components/ProjectTable.vue', 'projectFormDialogRef.edit()'],
    ['src/pages/project/components/ProjectMembersTab.vue', 'class="list-row-actions"'],
    ['src/pages/admin/backup/BackUpListPage.vue', '@click="confirmDeleteBackUp(row)"'],
    ['src/pages/admin/aggregate/AggregateListPage.vue', '`/admin/aggregate/${row.id}`'],
    ['src/pages/admin/volume/VolumeListPage.vue', '`/admin/volume/${row.id}`'],
    ['src/pages/admin/qtree/QtreeListPage.vue', '`/admin/qtree/${row.id}`'],
    ['src/pages/admin/user/UserListPage.vue', '@click="syncLdapUsers"'],
    ['src/pages/admin/ai/AiCenterPage.vue', '@click="addModel"'],
    ['src/pages/admin/storage-cluster/StorageClusterListPage.vue', 'formDialogRef.edit()'],
    ['src/pages/admin/storage-cluster/components/ClusterIncidentsTab.vue', 'openDetail(row)'],
    ['src/pages/incident/IncidentCenterPage.vue', 'openDetail(row)'],
  ])('%s keeps the operation column fixed on the right', (file, marker) => {
    const actions = columnContaining(readPage(file), marker);

    expect(actions).toContain('fixed="right"');
    expect(actions).toContain('align="right"');
    expect(actions).toMatch(/\bwidth="\d+"/);
  });

  it('never renders more than two direct controls in a table row action column', () => {
    const violations = [];

    for (const file of vueFiles(resolve(process.cwd(), 'src'))) {
      const source = readFileSync(file, 'utf8');
      for (const [column] of source.matchAll(/<ElTableColumn\b[\s\S]*?<\/ElTableColumn>/g)) {
        if (!/<template\s+#default/.test(column)) continue;

        const rowActions = column
          .replace(/<template\s+#header[\s\S]*?<\/template>/g, '')
          .replace(/<template\s+#dropdown[\s\S]*?<\/template>/g, '');
        const directControls = rowActions.match(/<(?:ElButton|ElLink)\b/g) ?? [];
        if (directControls.length > 2) {
          violations.push(`${file}: ${directControls.length}`);
        }
      }
    }

    expect(violations).toEqual([]);
  });

  it('keeps storage details direct and gates management actions and creation', () => {
    const actions = columnContaining(storageSource, '添加集群');
    const header = actions.match(/<template[\s\S]*?#header[^>]*>([\s\S]*?)<\/template>/)?.[1];

    expect(actions).toContain('width="132"');
    expect(actions).toContain('class="list-row-actions"');
    expect(actions.indexOf('详情')).toBeLessThan(actions.indexOf('<ElDropdown'));
    expect(actions).toMatch(/<ElDropdown[\s\S]*?v-if="hasRole\('disk-monitor:admin'\)"/);
    expect(actions).toContain('编辑');
    expect(actions).toContain('删除');
    expect(actions).toContain('class="list-row-actions__danger"');
    expect(header).toContain('v-if="hasRole(\'disk-monitor:admin\')"');
  });

  it('keeps AI editing direct and confirms deletion from the more menu', () => {
    const actions = columnContaining(aiSource, '新增模型');

    expect(actions).toContain('width="132"');
    expect(actions).toContain('class="list-row-actions"');
    expect(actions.indexOf('编辑')).toBeLessThan(actions.indexOf('<ElDropdown'));
    expect(actions).toContain('连接测试');
    expect(actions).toContain('删除');
    expect(actions).toContain('class="list-row-actions__danger"');
    expect(aiSource).toContain('ElMessageBox.confirm');
  });
});
