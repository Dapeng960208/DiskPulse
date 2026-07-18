import { flushPromises, shallowMount } from '@vue/test-utils';
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

    wrapper.vm.openCreateDialog();
    await wrapper.findComponent({ name: 'ElDialog' }).vm.$emit('update:modelValue', false);

    expect(wrapper.vm.createDialogVisible).toBe(false);
  });
});
