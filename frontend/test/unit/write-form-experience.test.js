import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

function source(path) {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

const dialogForms = [
  'src/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue',
  'src/pages/admin/user/components/UserFormDialog.vue',
  'src/pages/group/components/GroupFormDialog.vue',
  'src/pages/group-tag/components/GroupTagFormDialog.vue',
  'src/pages/project/components/ProjectFormDialog.vue',
  'src/pages/usage/components/UsageFormDialog.vue',
  'src/pages/admin/ai/AiCenterPage.vue',
];

describe('write form experience contract', () => {
  it.each(dialogForms)('%s uses the shared branded dialog structure', (path) => {
    const content = source(path);

    expect(content).toContain('write-form-dialog');
    expect(content).toContain('write-form-dialog__heading');
    expect(content).toContain('class="write-form"');
    expect(content).toContain('label-position="top"');
    expect(content).toContain('write-form-grid');
    expect(content).toContain(':before-close="beforeClose"');
  });

  it('uses concrete create and save button labels instead of a generic submit label', () => {
    for (const path of dialogForms) {
      const content = source(path);
      expect(content).not.toMatch(/>\s*提交\s*</);
      expect(content).toMatch(/创建|保存修改/);
    }
  });

  it('loads scoped global styles for branded dialogs, validation, and mobile fallback', () => {
    const styleEntry = source('src/styles/style.scss');
    const writeFormStyle = source('src/styles/write-form.scss');

    expect(styleEntry).toContain("@import './write-form.scss';");
    expect(writeFormStyle).toContain('.write-form-dialog');
    expect(writeFormStyle).toContain('.write-form-section');
    expect(writeFormStyle).toContain('.el-form-item.is-error');
    expect(writeFormStyle).toContain('@media (max-width:');
  });

  it('uses a branded page form and an explicit saving state for system settings', () => {
    const settings = source('src/pages/admin/settings/SettingsPage.vue');

    expect(settings).toContain('write-form-page');
    expect(settings).toContain('write-form-page__actions');
    expect(settings).toContain('class="write-form"');
    expect(settings).toContain('label-position="top"');
    expect(settings).toContain(':loading="saving"');
    expect(settings).toContain("saving ? '保存中…' : '保存设置'");
  });

  it('names high-risk confirmations after their object and action', () => {
    expect(source('src/pages/admin/storage-cluster/StorageClusterListPage.vue'))
      .toMatch(/删除存储集群[\s\S]*删除集群/);
    expect(source('src/pages/admin/user/UserListPage.vue'))
      .toMatch(/删除用户[\s\S]*删除用户/);
    expect(source('src/pages/group/GroupListPage.vue'))
      .toMatch(/删除项目组[\s\S]*删除项目组/);
    expect(source('src/pages/group-tag/GroupTagListPage.vue'))
      .toMatch(/删除项目组标签[\s\S]*删除标签/);
    expect(source('src/pages/admin/backup/BackUpListPage.vue'))
      .toMatch(/删除数据备份[\s\S]*删除备份[\s\S]*回滚数据备份[\s\S]*开始回滚/);
    expect(source('src/pages/usage/UsageListPage.vue'))
      .toMatch(/移动用户目录[\s\S]*移动目录/);
  });
});
