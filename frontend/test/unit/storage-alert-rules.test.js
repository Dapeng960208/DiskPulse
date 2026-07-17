import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const projectApi = vi.hoisted(() => ({ fetchById: vi.fn() }));
const configApi = vi.hoisted(() => ({ fetch: vi.fn() }));
vi.mock('@/api/project-api', () => ({ default: projectApi }));
vi.mock('@/api/config-api', () => ({ default: configApi }));
vi.mock('@/api/users-api', () => ({
  default: { fetch: vi.fn(() => Promise.resolve({ content: [] })), fetchById: vi.fn() },
}));

function source(path) {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

describe('storage alert rule UI contract', () => {
  it('provides one shared rule form with quota, threshold, and repeat validation', () => {
    const form = source('src/components/form/StorageAlertRuleForm.vue');

    expect(form).toContain('quota_basis');
    expect(form).toContain('threshold');
    expect(form).toContain('repeat_hours');
    expect(form).toContain('value="hard"');
    expect(form).toContain('value="soft"');
    expect(form).toContain('重要');
    expect(form).toContain('严重');
    expect(form).toContain('紧急');
    expect(form).toContain(':min="1"');
    expect(form).toContain(':max="100"');
    expect(form).toContain('重要阈值必须小于严重阈值');
    expect(form).toContain('严重阈值必须小于紧急阈值');
  });

  it('reports an invalid cross-level threshold order', async () => {
    const { default: StorageAlertRuleForm } = await import(
      '@/components/form/StorageAlertRuleForm.vue'
    );
    const rule = {
      quota_basis: 'hard',
      important: { threshold: 80, repeat_hours: 24 },
      serious: { threshold: 90, repeat_hours: 6 },
      emergency: { threshold: 95, repeat_hours: 1 },
    };
    const wrapper = shallowMount(StorageAlertRuleForm, { props: { modelValue: rule } });

    await wrapper.setProps({
      modelValue: { ...rule, important: { threshold: 90, repeat_hours: 24 } },
    });

    expect(wrapper.emitted('validity-change').at(-1)).toEqual([false]);
  });

  it('shows the system rule directly in superadmin-only storage settings', () => {
    const settings = source('src/pages/admin/settings/SettingsPage.vue');
    const routes = source('src/router/routes.js');

    expect(settings).toContain('StorageAlertRuleForm');
    expect(settings).toContain('<h2>系统设置</h2>');
    expect(settings).not.toContain('<ElTabs');
    expect(settings).toContain('v-model="form.storage_alert_rule"');
    expect(routes).toMatch(/path: 'settings',[\s\S]*?meta: \{[^}]*title: '系统设置',[^}]*isAccessible: \(\) => hasRole\('superadmin'\) \? 200 : 403,?[^}]*\}/);
  });

  it('submits project alert enablement and an optional complete override', () => {
    const project = source('src/pages/project/components/ProjectFormDialog.vue');

    expect(project).toContain('is_alert');
    expect(project).toContain('storage_alert_rule');
    expect(project).toContain('StorageAlertRuleForm');
    expect(project).toContain('项目告警');
    expect(project).toContain('自定义告警规则');
    expect(project).toContain('继承系统规则');
    expect(project).toMatch(/projectApi\.(create|replace)\([\s\S]*storage_alert_rule|storage_alert_rule[\s\S]*projectApi\.(create|replace)\(/);
  });

  it('submits group inheritance and multiple individual Feishu CC users', () => {
    const group = source('src/pages/group/components/GroupFormDialog.vue');

    expect(group).toContain('storage_alert_rule');
    expect(group).toContain('alert_cc_user_ids');
    expect(group).toContain('StorageAlertRuleForm');
    expect(group).toContain('自定义告警规则');
    expect(group).toContain('继承');
    expect(group).toMatch(/<RdUserSelect[\s\S]*v-model="model\.alert_cc_user_ids"[\s\S]*multiple/);
    expect(group).toMatch(/groupApi\.(create|replace)\([\s\S]*alert_cc_user_ids|alert_cc_user_ids[\s\S]*groupApi\.(create|replace)\(/);
  });

  it('loads the full project before previewing an inherited project rule', async () => {
    const systemRule = {
      quota_basis: 'hard',
      important: { threshold: 80, repeat_hours: 24 },
      serious: { threshold: 90, repeat_hours: 6 },
      emergency: { threshold: 95, repeat_hours: 1 },
    };
    const projectRule = {
      ...systemRule,
      important: { threshold: 70, repeat_hours: 12 },
    };
    configApi.fetch.mockResolvedValue({ storage_alert_rule: systemRule });
    projectApi.fetchById.mockResolvedValue({ id: 7, name: 'Project 7', storage_alert_rule: projectRule });
    const { default: GroupFormDialog } = await import(
      '@/pages/group/components/GroupFormDialog.vue'
    );
    const wrapper = shallowMount(GroupFormDialog, {
      global: { renderStubDefaultSlot: true },
    });

    wrapper.vm.$.exposed.edit({
      id: 3,
      name: 'Group 3',
      project_id: 7,
      project: { id: 7, name: 'Project 7' },
      storage_cluster_id: 2,
      storage_cluster: { id: 2, name: 'Cluster 2', storage_type: 'netapp' },
      group_tag_id: 4,
      enable_monitoring: true,
      storage_alert_rule: null,
    });
    await flushPromises();

    expect(projectApi.fetchById).toHaveBeenCalledWith(7);
    expect(wrapper.find('el-alert-stub').attributes('title')).toBe('继承项目规则');
    expect(wrapper.findComponent('storage-alert-rule-form-stub').props('modelValue')).toEqual(projectRule);
  });

  it('filters and displays storage alert event, quota, and delivery fields', () => {
    const alerts = source('src/pages/alert/AlertListPage.vue');

    expect(alerts).toContain("case 'alert':");
    expect(alerts).toContain("'用户目录': 'StorageUsage'");
    expect(alerts).toContain("'项目组': 'Group'");
    expect(alerts).toContain("'项目': 'Project'");
    expect(alerts).toContain("row.project_name || row.related_info?.context?.project || '-'");
    expect(alerts).toContain("row.cluster_name || row.related_info?.context?.cluster");
    expect(alerts).toContain('label="集群"');
    expect(alerts).toContain(
      "row.related_info?.context?.group_tag || row.related_info?.group_tag?.name || '-'",
    );
    expect(alerts).toContain('alertDescription(row)');
    expect(alerts).toContain('context.linux_path');
    expect(alerts).toContain('`Linux目录 ${context.linux_path}`');
    expect(alerts).not.toContain('`集群 ${context.cluster} 项目 ${context.project}');
    expect(alerts).toContain("important: '重要'");
    expect(alerts).toContain("serious: '严重'");
    expect(alerts).toContain("emergency: '紧急'");
    expect(alerts).toContain("StorageUsage: '用户目录'");
    expect(alerts).toContain("repeat: '重复告警'");
    for (const field of ['event_type', 'quota_basis', 'delivery_status']) {
      expect(alerts).toContain(field);
      expect(alerts).toContain(`prop="${field}"`);
    }
    for (const label of [
      '首次告警', '告警升级', '重复告警', '恢复通知',
      '硬限额', '软限额', '待发送', '重试中', '已发送', '发送失败', '已跳过',
    ]) {
      expect(alerts).toContain(label);
    }
  });

  it('does not render quota adjustment limits as alert usage percentages', () => {
    const alerts = source('src/pages/alert/AlertListPage.vue');

    expect(alerts).toContain("{ value: 'quota_adjustment', label: '配额调整' }");
    expect(alerts).toContain("if (row.alert_type !== 'alert') return row.description || '-';");
    expect(alerts).toContain("const alertField = (row, value) => row.alert_type === 'alert' ? value ?? '-' : '-';");
    expect(alerts).toContain('alertField(row, row.threshold)');
    expect(alerts).toContain('alertField(row, row.avg_use_ratio)');
  });

  it('keeps the existing CRUD endpoints that carry the new fields and filters', () => {
    expect(source('src/api/config-api.js')).toContain("new ConfigApi('/config/storage')");
    expect(source('src/api/project-api.js')).toContain("new ProjectApi('/projects/')");
    expect(source('src/api/group-api.js')).toContain("new GroupApi('/groups/')");
    expect(source('src/api/alert-api.js')).toContain("new AlertApi('/storage-alerts/')");
  });
});
