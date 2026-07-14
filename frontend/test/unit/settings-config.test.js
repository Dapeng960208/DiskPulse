import { flushPromises, shallowMount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const configApi = vi.hoisted(() => ({
  fetch: vi.fn(),
  updateConfig: vi.fn(),
}));

vi.mock('@/api/config-api', () => ({ default: configApi }));

const InputNumberStub = {
  name: 'ElInputNumber',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input />',
};

describe('storage settings configuration source', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configApi.fetch.mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not expose ineffective QuestDB connection fields', async () => {
    const { default: SettingsPage } = await import(
      '@/pages/admin/settings/SettingsPage.vue'
    );
    const wrapper = shallowMount(SettingsPage, {
      global: {
        renderStubDefaultSlot: true,
        stubs: { ElInputNumber: InputNumberStub },
      },
    });
    await flushPromises();

    const tabLabels = wrapper
      .findAllComponents({ name: 'ElTabPane' })
      .map((tab) => tab.props('label'));

    expect(tabLabels).not.toContain('时序数据库配置');
    expect(wrapper.html()).not.toMatch(/questdb_(host|port|user|password)/);
  });

  it('loads editable settings and saves the updated form', async () => {
    const initialConfig = {
      mail_host: 'mail_host',
      mail_port: 'mail_port',
      mail_user: 'mail_user',
      mail_password: 'mail_password',
      mail_to: 'mail_to',
      company: 'company',
      domain_name: 'domain_name',
      person_expand: 'person_expand',
      group_expand: 'group_expand',
      iam_url: 'iam_url',
      iam_account: 'iam_account',
      iam_password: 'iam_password',
      storage_host: 'storage_host',
      storage_port: 'storage_port',
      storage_user: 'storage_user',
      storage_password: 'storage_password',
      back_up_enabled: true,
      file_manage_host: 'file_manage_host',
      file_manage_port: 'file_manage_port',
      file_manage_user: 'file_manage_user',
      file_manage_password: 'file_manage_password',
      back_up_quit_days: 10,
      back_up_dir: 'back_up_dir',
      back_up_duration: 20,
      bpm_process_id: 'bpm_process_id',
      bpm_api_url: 'bpm_api_url',
    };
    configApi.fetch.mockResolvedValue(initialConfig);
    configApi.updateConfig.mockImplementation(async (config) => config);

    const { ElMessage } = await import('element-plus');
    const success = vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    const { default: SettingsPage } = await import(
      '@/pages/admin/settings/SettingsPage.vue'
    );
    const wrapper = shallowMount(SettingsPage, {
      global: {
        renderStubDefaultSlot: true,
        stubs: { ElInputNumber: InputNumberStub },
      },
    });
    await flushPromises();

    const expected = { ...initialConfig };
    for (const input of wrapper.findAllComponents({ name: 'ElInput' })) {
      const field = input.props('modelValue');
      expected[field] = `updated-${field}`;
      input.vm.$emit('update:modelValue', expected[field]);
    }
    const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' });
    numberInputs[0].vm.$emit('update:modelValue', 30);
    numberInputs[1].vm.$emit('update:modelValue', 40);
    expected.back_up_quit_days = 30;
    expected.back_up_duration = 40;
    wrapper
      .findComponent({ name: 'ElSwitch' })
      .vm.$emit('update:modelValue', false);
    expected.back_up_enabled = false;

    await wrapper.findComponent({ name: 'ElButton' }).trigger('click');
    await flushPromises();

    expect(configApi.updateConfig).toHaveBeenCalledWith(expected);
    expect(success).toHaveBeenCalledWith('保存成功');
  });
});
