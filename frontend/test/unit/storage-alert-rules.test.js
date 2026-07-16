import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

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

  it('adds the system rule to superadmin-only storage settings', () => {
    const settings = source('src/pages/admin/settings/SettingsPage.vue');
    const routes = source('src/router/routes.js');

    expect(settings).toContain('StorageAlertRuleForm');
    expect(settings).toContain('label="存储告警规则"');
    expect(settings).toContain('v-model="form.storage_alert_rule"');
    expect(routes).toMatch(/path: 'settings',[\s\S]*?meta: \{\s*title: '系统设置',\s*isAccessible: \(\) => hasRole\('superadmin'\) \? 200 : 403,?\s*\}/);
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

  it('filters and displays storage alert event, quota, and delivery fields', () => {
    const alerts = source('src/pages/alert/AlertListPage.vue');

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

  it('keeps the existing CRUD endpoints that carry the new fields and filters', () => {
    expect(source('src/api/config-api.js')).toContain("new ConfigApi('/config/storage')");
    expect(source('src/api/project-api.js')).toContain("new ProjectApi('/projects/')");
    expect(source('src/api/group-api.js')).toContain("new GroupApi('/groups/')");
    expect(source('src/api/alert-api.js')).toContain("new AlertApi('/storage-alerts/')");
  });
});
