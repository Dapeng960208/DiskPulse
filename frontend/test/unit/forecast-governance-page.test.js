import { flushPromises, shallowMount } from '@vue/test-utils';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { nextTick } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({
  settings: vi.fn(),
  fetchCandidates: vi.fn(),
  updateSettings: vi.fn(),
  createCandidate: vi.fn(),
  activateCandidate: vi.fn(),
}));
const aiApi = vi.hoisted(() => ({
  listAdminModels: vi.fn(),
}));

vi.mock('@/api/capacity-prediction-api.js', () => ({ default: api }));
vi.mock('@/api/ai-api.js', () => ({ default: aiApi }));

import ForecastGovernancePage from '@/pages/admin/forecast-governance/ForecastGovernancePage.vue';

const mountPage = () => shallowMount(ForecastGovernancePage, {
  global: { directives: { loading: () => {} } },
});

describe('ForecastGovernancePage', () => {
  beforeEach(() => {
    api.settings.mockResolvedValue({ visible: false });
    api.fetchCandidates.mockResolvedValue([{
      id: 4,
      version: 'capacity-ai-v2',
      ai_model_id: 3,
      activation_ready: true,
      enabled: false,
      evaluations: [],
    }]);
    api.updateSettings.mockResolvedValue({ visible: true });
    api.createCandidate.mockResolvedValue({ id: 5 });
    api.activateCandidate.mockResolvedValue({ id: 4, enabled: true });
    aiApi.listAdminModels.mockResolvedValue([
      { id: 3, name: '公有预测模型', provider: 'openai', model: 'gpt-forecast', enabled: false },
      { id: 4, name: '本地预测模型', provider: 'ollama', model: 'forecast-local', enabled: true },
    ]);
  });

  it('updates global visibility and reports save failures', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.vm.update(true);
    expect(api.updateSettings).toHaveBeenCalledWith({ user_visible: true });
    expect(wrapper.vm.visible).toBe(true);

    api.updateSettings.mockRejectedValue(new Error('unavailable'));
    await wrapper.vm.update(false);
    expect(wrapper.vm.error).toBe('保存预测可见性失败');
  });

  it('keeps visibility and candidate creation in one compact control row', async () => {
    const wrapper = mountPage();
    await flushPromises();

    const controlRow = wrapper.find('.forecast-governance-page__setting');
    expect(wrapper.find('.forecast-governance-page__header').exists()).toBe(false);
    expect(wrapper.find('h2').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('后台预测和评估持续运行');
    expect(controlRow.text()).toContain('全局用户可见性');
    expect(controlRow.findComponent({ name: 'ElButton' }).exists()).toBe(true);
  });

  it('explains both MAPE metrics and keeps the evaluation table directly below its heading', () => {
    const source = readFileSync(resolve('src/pages/admin/forecast-governance/ForecastGovernancePage.vue'), 'utf8');

    expect(source).toContain('基线 MAPE：当前基线预测与实际容量的平均绝对百分比误差，数值越低越准确。');
    expect(source).toContain('候选 MAPE：候选 AI 模型预测与实际容量的平均绝对百分比误差，数值越低越准确。');
    expect(source).toContain('aria-label="基线 MAPE 说明"');
    expect(source).toContain('aria-label="候选 MAPE 说明"');
    expect(source).not.toContain('grid-template-rows: auto auto minmax(0, 1fr)');
  });

  it('keeps the control row and both table headings at their contracted dimensions', () => {
    const source = readFileSync(resolve('src/pages/admin/forecast-governance/ForecastGovernancePage.vue'), 'utf8');

    expect(source).toContain('.forecast-governance-page__setting { display: flex; align-items: center; gap: var(--spacing-md); height: 60px; }');
    expect(source.match(/class="forecast-governance-page__section-heading"/g)).toHaveLength(2);
    expect(source).toContain('.forecast-governance-page__section-heading { display: flex; align-items: center; justify-content: flex-start; height: 40px; text-align: left; }');
    expect(source).toContain('.forecast-governance-page { display: grid; align-content: start; gap: var(--spacing-lg); }');
    expect(source).toContain('.forecast-governance-page__section { display: grid; align-content: start; gap: var(--spacing-md); }');
  });

  it('creates a trimmed candidate and reloads governance state', async () => {
    const wrapper = mountPage();
    await flushPromises();

    wrapper.vm.openCreateDialog();
    wrapper.vm.candidateForm.version = '  capacity-ai-v3  ';
    wrapper.vm.candidateForm.aiModelId = 12;
    await wrapper.vm.createCandidate();

    expect(api.createCandidate).toHaveBeenCalledWith({ version: 'capacity-ai-v3', ai_model_id: 12 });
    expect(api.settings).toHaveBeenCalledTimes(2);
    expect(wrapper.vm.createDialogVisible).toBe(false);
  });

  it('offers every AI Center model in the candidate-model dropdown without provider or enabled filtering', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.vm.openCreateDialog();

    expect(aiApi.listAdminModels).toHaveBeenCalledTimes(1);
    expect(wrapper.vm.configuredModels).toEqual([
      { id: 3, name: '公有预测模型', provider: 'openai', model: 'gpt-forecast', enabled: false },
      { id: 4, name: '本地预测模型', provider: 'ollama', model: 'forecast-local', enabled: true },
    ]);
  });

  it('activates an eligible candidate and reports a rejected activation', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.vm.activateCandidate({ id: 4 });
    expect(api.activateCandidate).toHaveBeenCalledWith(4);
    expect(wrapper.vm.activatingId).toBe(null);

    api.activateCandidate.mockRejectedValue(new Error('not ready'));
    await wrapper.vm.activateCandidate({ id: 6 });
    expect(wrapper.vm.error).toContain('三窗口准确率与风险覆盖门槛');
  });

  it('updates dialog visibility through the v-model contract', async () => {
    const wrapper = mountPage();
    await flushPromises();

    await wrapper.vm.openCreateDialog();
    await wrapper.findComponent({ name: 'ElDialog' }).vm.$emit('update:modelValue', false);
    await nextTick();

    expect(wrapper.vm.createDialogVisible).toBe(false);
  });
});
