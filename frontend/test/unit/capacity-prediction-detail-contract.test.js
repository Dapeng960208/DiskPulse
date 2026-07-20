import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('resource capacity prediction detail contracts', () => {
  it('keeps capacity prediction in a standalone root entry while preserving resource deep links', () => {
    const group = source('src/pages/group/GroupDetailPage.vue');
    const usage = source('src/pages/usage/UsageDetailPage.vue');
    const routes = source('src/router/routes.js');

    expect(group).not.toContain('CapacityPredictionPanel');
    expect(usage).not.toContain('CapacityPredictionPanel');
    expect(routes).toContain("name: 'CapacityPredictions'");
    expect(routes).toContain("name: 'UsageCapacityPrediction'");
    expect(routes).toContain("name: 'GroupCapacityPrediction'");
  });

  it('keeps prediction visibility server-driven and scoped by resource type', () => {
    const panel = source('src/pages/capacity-prediction/CapacityPredictionPanel.vue');
    const api = source('src/api/capacity-prediction-api.js');

    expect(panel).toContain('visible');
    expect(panel).toContain('assetType');
    expect(api).toContain('/capacity-predictions/');
  });

  it('lets project administrators maintain structured plans and super administrators govern candidates', () => {
    const panel = source('src/pages/capacity-prediction/CapacityPredictionPanel.vue');
    const governance = source('src/pages/admin/forecast-governance/ForecastGovernancePage.vue');
    const api = source('src/api/capacity-prediction-api.js');

    expect(panel).toContain('createPlan');
    expect(panel).toContain('canManagePlans');
    expect(governance).toContain('fetchCandidates');
    expect(governance).toContain('createCandidate');
    expect(governance).toContain('activateCandidate');
    expect(governance).toContain('评估窗口');
    expect(governance).toContain('AI 回退');
    expect(governance).toContain('fallback_count');
    expect(governance).toContain('Array.isArray');
    expect(api).toContain('capacity-prediction-candidates');
    expect(api).toContain('createCandidate');
  });

  it('explains prediction confidence, model fallback, and related incident boundaries', () => {
    const panel = source('src/pages/capacity-prediction/CapacityPredictionPanel.vue');

    expect(panel).toContain('数据质量');
    expect(panel).toContain('模型版本');
    expect(panel).toContain('关联事件');
    expect(panel).toContain('基线回退');
    expect(panel).toContain('auditSummary');
    expect(panel).toContain('relatedIncidents');
  });
});
