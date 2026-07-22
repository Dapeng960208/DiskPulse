import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('four-dimension capacity exhaustion risk contract', () => {
  const cluster = source('src/pages/admin/storage-cluster/StorageClusterDetailPage.vue');
  const project = source('src/pages/project/ProjectDetailPage.vue');
  const group = source('src/pages/group/GroupDetailPage.vue');
  const usage = source('src/pages/usage/UsageDetailPage.vue');

  it.each([
    ['storage cluster', cluster, 'storage_cluster'],
    ['project', project, 'project'],
    ['project group', group, 'group'],
    ['user directory', usage, 'storage_usage'],
  ])('mounts the shared risk panel in the %s detail', (_, page, assetType) => {
    expect(page).toContain("import('@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue')");
    expect(page).toContain('label="耗尽风险"');
    expect(page).toContain(`asset-type="${assetType}"`);
  });

  it('does not keep the old full prediction panel in resource details', () => {
    for (const page of [cluster, project, group, usage]) {
      expect(page).not.toContain('CapacityPredictionPanel');
      expect(page).not.toContain('容量预测最终结果');
    }
  });
});
