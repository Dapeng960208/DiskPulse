import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

function actionColumn(page) {
  const start = page.lastIndexOf('<ElTableColumn');
  return page.slice(start, page.indexOf('</ElTableColumn>', start));
}

describe('list capacity prediction navigation', () => {
  const usageList = source('src/pages/usage/UsageListPage.vue');
  const groupList = source('src/pages/group/GroupListPage.vue');
  const routes = source('src/router/routes.js');

  it.each([
    ['user directory', usageList, 'UsageCapacityPrediction'],
    ['project group', groupList, 'GroupCapacityPrediction'],
  ])('puts the %s prediction entry in the row more-actions menu', (_, page, routeName) => {
    const actions = actionColumn(page);

    expect(page).toContain('capacityPredictionApi.visibility()');
    expect(page).toContain('openCapacityPrediction');
    expect(actions).toContain('容量预测');
    expect(page).toContain(`router.push({ name: '${routeName}'`);
    expect(actions).toContain('@click="openCapacityPrediction(row)"');
    expect(actions).not.toContain('capacity-prediction-entry');
  });

  it('routes list actions to the standalone prediction detail page', () => {
    expect(routes).toContain("path: 'usage/:id/capacity-prediction'");
    expect(routes).toContain("name: 'UsageCapacityPrediction'");
    expect(routes).toContain("path: 'group/:id/capacity-prediction'");
    expect(routes).toContain("name: 'GroupCapacityPrediction'");
    expect(routes).toContain("import('@/pages/capacity-prediction/CapacityPredictionDetailPage.vue')");
  });
});
