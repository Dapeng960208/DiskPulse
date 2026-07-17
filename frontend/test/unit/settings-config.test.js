import { flushPromises, shallowMount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const configApi = vi.hoisted(() => ({
  fetch: vi.fn(),
  updateConfig: vi.fn(),
}));

vi.mock('@/api/config-api', () => ({ default: configApi }));

const storageAlertRule = {
  quota_basis: 'hard',
  important: { threshold: 70, repeat_hours: 24 },
  serious: { threshold: 80, repeat_hours: 12 },
  emergency: { threshold: 90, repeat_hours: 6 },
};

async function mountSettings(config = { storage_alert_rule: storageAlertRule }) {
  configApi.fetch.mockResolvedValue(config);
  const { default: SettingsPage } = await import(
    '@/pages/admin/settings/SettingsPage.vue'
  );
  const wrapper = shallowMount(SettingsPage, {
    global: {
      renderStubDefaultSlot: true,
      plugins: [createPinia()],
    },
  });
  await flushPromises();
  return wrapper;
}

describe('system settings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows only the ordinary title and storage alert rule form', async () => {
    const wrapper = await mountSettings();

    expect(wrapper.find('h2').text()).toBe('系统设置');
    expect(wrapper.find('.write-form-page__header').exists()).toBe(false);
    expect(wrapper.find('p').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'ElTabs' }).exists()).toBe(false);
    expect(wrapper.findAllComponents({ name: 'ElTabPane' })).toHaveLength(0);
    expect(wrapper.findAllComponents({ name: 'ElInput' })).toHaveLength(0);
    expect(wrapper.findComponent({ name: 'StorageAlertRuleForm' }).exists()).toBe(true);
    expect(wrapper.text()).not.toMatch(/邮箱配置|邮件链接|IAM相关配置|存储配置/);
  });

  it('preserves hidden mail settings when saving the alert rule', async () => {
    const config = {
      mail_host: 'smtp.example.com',
      mail_port: '587',
      mail_user: 'diskpulse',
      mail_password: 'secret',
      mail_to: 'ops@example.com',
      company: 'DiskPulse',
      domain_name: 'https://diskpulse.example.com',
      person_expand: '/person-expand',
      group_expand: '/group-expand',
      storage_alert_rule: storageAlertRule,
    };
    configApi.updateConfig.mockResolvedValue(config);
    const { ElMessage } = await import('element-plus');
    const success = vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    const wrapper = await mountSettings(config);

    await wrapper.findComponent({ name: 'ElButton' }).trigger('click');
    await flushPromises();

    expect(configApi.updateConfig).toHaveBeenCalledWith(config);
    expect(success).toHaveBeenCalledWith('系统设置已保存');
  });
});
