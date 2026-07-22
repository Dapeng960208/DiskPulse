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
    ['user directory', usageList],
    ['project group', groupList],
  ])('removes the standalone prediction action from the %s list', (_, page) => {
    const actions = actionColumn(page);

    expect(page).not.toContain('capacityPredictionApi.visibility()');
    expect(page).not.toContain('openCapacityPrediction');
    expect(actions).not.toContain('容量预测');
  });

  it('keeps old prediction deep links only as redirects to resource details', () => {
    expect(routes).toContain("path: 'usage/:id/capacity-prediction'");
    expect(routes).toContain("name: 'UsageCapacityPrediction'");
    expect(routes).toContain("path: 'group/:id/capacity-prediction'");
    expect(routes).toContain("name: 'GroupCapacityPrediction'");
    expect(routes).toContain("redirect: (to) => ({ name: 'UsagesDetail', params: { id: to.params.id } })");
    expect(routes).toContain("redirect: (to) => ({ name: 'GroupDetail', params: { id: to.params.id } })");
    expect(routes).not.toContain("import('@/pages/capacity-prediction/CapacityPredictionDetailPage.vue')");
  });
});
