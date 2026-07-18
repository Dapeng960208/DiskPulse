import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('resource capacity prediction detail contracts', () => {
  it('adds lazy capacity prediction tabs to group and user-directory details', () => {
    const group = source('src/pages/group/GroupDetailPage.vue');
    const usage = source('src/pages/usage/UsageDetailPage.vue');

    expect(group).toContain('CapacityPredictionPanel');
    expect(usage).toContain('CapacityPredictionPanel');
    expect(group).toContain('容量预测');
    expect(usage).toContain('容量预测');
  });

  it('keeps prediction visibility server-driven and scoped by resource type', () => {
    const panel = source('src/pages/capacity-prediction/CapacityPredictionPanel.vue');
    const api = source('src/api/capacity-prediction-api.js');

    expect(panel).toContain('visible');
    expect(panel).toContain('assetType');
    expect(api).toContain('/capacity-predictions/');
  });
});
