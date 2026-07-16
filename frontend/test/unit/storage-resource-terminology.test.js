import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

function source(path) {
  return readFileSync(resolve(process.cwd(), path), 'utf8');
}

describe('cross-vendor storage resource terminology', () => {
  it('uses capacity-pool and storage-space labels on resource pages', () => {
    const aggregate = source('src/pages/admin/aggregate/AggregateListPage.vue');
    const volume = source('src/pages/admin/volume/VolumeListPage.vue');
    const qtree = source('src/pages/admin/qtree/QtreeListPage.vue');

    expect(aggregate).toContain('label="容量池名"');
    expect(aggregate).toContain('label="原生类型"');
    expect(aggregate).toContain('/admin/aggregate/');

    expect(volume).toContain('label="存储空间名"');
    expect(volume).toContain('label="所属容量池"');
    expect(volume).toContain('label="原生类型"');
    expect(volume).toContain('label="服务域（SVM / Access Zone）"');
    expect(volume).toContain('show-overflow-tooltip');
    expect(volume).toContain('/admin/volume/');
    expect(volume.match(/label="状态"/g)).toHaveLength(1);

    expect(qtree).toContain('Qtree（NetApp）');
    expect(qtree).toContain('label="所属存储空间"');
    expect(qtree).toContain('/admin/qtree/');
  });

  it('shows one localized storage target across group, project, and usage pages', () => {
    const groupForm = source('src/pages/group/components/GroupFormDialog.vue');
    const groupList = source('src/pages/group/GroupListPage.vue');
    const groupDetail = source('src/pages/group/GroupDetailPage.vue');
    const projectDetail = source('src/pages/project/ProjectDetailPage.vue');
    const usageList = source('src/pages/usage/UsageListPage.vue');

    expect(groupForm).toContain('存储空间（Directory Quota）');
    expect(groupForm).toContain('Qtree（NetApp）');
    expect(groupForm).toContain('单个存储目标关联多个项目组');
    expect(groupList).toContain('存储目标');
    expect(groupDetail).toContain('info?.storage_target');
    expect(projectDetail).toContain('formatStorageTargetType');
    expect(usageList).toContain('label="存储类型"');
    expect(usageList).not.toContain('label="Volume"');
    expect(usageList).not.toContain('label="Qtree"');
  });

  it('localizes alert categories and the realtime empty state while accepting groups', () => {
    const alert = source('src/pages/alert/AlertListPage.vue');
    const realtime = source('src/pages/common/RealTimePage.vue');

    expect(alert).toContain("'容量池': 'Aggregate'");
    expect(alert).toContain("'存储空间': 'Volume'");
    expect(alert).toContain("'Qtree（NetApp）': 'Qtree'");
    expect(alert).toContain("case 'vendor_event':");
    expect(alert).toContain("return '系统事件';");
    expect(realtime).toMatch(/validator:[\s\S]*'group'/);
    expect(realtime).toContain("'暂无趋势数据'");
    expect(realtime).not.toContain("'NO DATA'");
  });

  it('exposes each storage cluster protocol and TLS verification state where configured', () => {
    const form = source('src/pages/admin/storage-cluster/components/StorageClusterFormDialog.vue');
    const list = source('src/pages/admin/storage-cluster/StorageClusterListPage.vue');

    expect(form).toContain('label="访问协议"');
    expect(form).toContain('label="TLS 证书校验"');
    expect(list).toContain('label="协议"');
    expect(list).toContain('label="TLS 校验"');
  });
});
