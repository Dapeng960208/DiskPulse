import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(
  resolve(process.cwd(), 'src/pages/project/components/ProjectGroupsTab.vue'),
  'utf8',
);

function actionColumn() {
  const start = source.lastIndexOf('<ElTableColumn');
  return source.slice(start, source.indexOf('</ElTableColumn>', start));
}

describe('ProjectGroupsTab actions', () => {
  it('restores a fixed right-side operation column for project groups', () => {
    const actions = actionColumn();

    expect(actions).toContain('label="操作"');
    expect(actions).toContain('fixed="right"');
    expect(actions).toContain('align="right"');
    expect(actions).toMatch(/width="\d+"/);
  });

  it('limits project-group creation and editing to super administrators', () => {
    const actions = actionColumn();
    const header = actions.match(/<template[\s\S]*?#header[^>]*>([\s\S]*?)<\/template>/)?.[1];

    expect(source).toContain("import { hasRole } from '@/utils/authorization';");
    expect(header).toContain('v-if="hasRole(\'disk-monitor:admin\')"');
    expect(header).toContain('添加项目组');
    expect(actions).toContain('v-if="hasRole(\'disk-monitor:admin\')"');
    expect(actions).toContain('编辑');
    expect(actions).toContain('groupFormDialogRef.edit()');
    expect(actions).toContain('groupFormDialogRef.edit(row)');
  });

  it('restores quota adjustment only when the server grants the row capability', () => {
    const actions = actionColumn();

    expect(source).toContain('function canAdjustQuota(row)');
    expect(source).toContain('row?.capabilities?.adjust_quota === true');
    expect(actions).toContain('v-if="canAdjustQuota(row)"');
    expect(actions).toContain('调整额度');
    expect(actions).toContain('quotaAdjustmentDialogRef.open(row)');
  });
});
