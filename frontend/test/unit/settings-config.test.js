import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const configApi = vi.hoisted(() => ({
  fetch: vi.fn(),
  updateConfig: vi.fn(),
}));

vi.mock('@/api/config-api', () => ({ default: configApi }));

describe('storage settings configuration source', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configApi.fetch.mockResolvedValue({});
  });

  it('does not expose ineffective QuestDB connection fields', async () => {
    const { default: SettingsPage } = await import(
      '@/pages/admin/settings/SettingsPage.vue'
    );
    const wrapper = shallowMount(SettingsPage, {
      global: { renderStubDefaultSlot: true },
    });
    await flushPromises();

    const tabLabels = wrapper
      .findAllComponents({ name: 'ElTabPane' })
      .map((tab) => tab.props('label'));

    expect(tabLabels).not.toContain('时序数据库配置');
    expect(wrapper.html()).not.toMatch(/questdb_(host|port|user|password)/);
  });
});
