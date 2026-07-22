import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ fetchRisk: vi.fn() }));
vi.mock('@/api/capacity-prediction-api.js', () => ({ default: api }));

import CapacityExhaustionRiskPanel from '@/pages/capacity-prediction/CapacityExhaustionRiskPanel.vue';

const mountPanel = (props = {}) => shallowMount(CapacityExhaustionRiskPanel, {
  props: { assetType: 'project', assetId: 11, ...props },
  global: { directives: { loading: () => undefined } },
});

describe('CapacityExhaustionRiskPanel', () => {
  beforeEach(() => {
    api.fetchRisk.mockReset();
    api.fetchRisk.mockResolvedValue({
      level: 'critical',
      label: '紧急',
      p50_exhaustion_at: null,
      p90_exhaustion_at: '2026-07-28T00:00:00Z',
      horizon_days: 30,
      reason: 'P90 预计在 7 日内达到硬限额',
      generated_at: '2026-07-22T00:00:00Z',
    });
  });

  it('loads and displays only the server-side exhaustion-risk conclusion', async () => {
    const wrapper = mountPanel();
    await flushPromises();

    expect(api.fetchRisk).toHaveBeenCalledWith('project', 11, { errorHandlerDisabled: true });
    expect(wrapper.text()).toContain('紧急');
    expect(wrapper.text()).toContain('P90 预计在 7 日内达到硬限额');
    expect(wrapper.text()).toContain('2026-07-28');
    expect(wrapper.text()).not.toContain('MAPE');
    expect(wrapper.text()).not.toContain('模型版本');
    expect(wrapper.text()).not.toContain('容量计划');
    expect(wrapper.text()).not.toContain('关联事件');
  });

  it('distinguishes insufficient data from no exhaustion risk', async () => {
    api.fetchRisk.mockResolvedValue({
      level: 'insufficient',
      label: '数据不足',
      p50_exhaustion_at: null,
      p90_exhaustion_at: null,
      horizon_days: 30,
      reason: '有效日少于 30 天或覆盖率低于 80%',
      generated_at: '2026-07-22T00:00:00Z',
    });

    const wrapper = mountPanel();
    await flushPromises();

    expect(wrapper.text()).toContain('数据不足');
    expect(wrapper.text()).not.toContain('30 日内无耗尽风险');
  });

  it('shows a stable empty state for a missing forecast and a safe error otherwise', async () => {
    api.fetchRisk.mockRejectedValueOnce({ response: { status: 404 } });
    const empty = mountPanel();
    await flushPromises();
    expect(empty.text()).toContain('暂无耗尽风险结果');

    api.fetchRisk.mockRejectedValueOnce(new Error('unavailable'));
    const failed = mountPanel({ assetType: 'storage_cluster', assetId: 21 });
    await flushPromises();
    expect(failed.text()).toContain('加载耗尽风险失败');
  });
});
