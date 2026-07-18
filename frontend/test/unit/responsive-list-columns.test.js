import fs from 'node:fs';
import path from 'node:path';
import { useResponsiveTableColumns } from '@/composables/responsive-table-columns';

let viewportWidth = 1600;

vi.mock('@vueuse/core', () => ({
  useMediaQuery: (query) => ({
    value: viewportWidth >= Number(query.match(/\d+/)?.[0]),
  }),
}));

const pageContracts = [
  {
    file: 'src/pages/usage/UsageListPage.vue',
    progress: ['硬限额使用率(%)', '软限额使用率(%)'],
    secondary: ['项目组标签', '存储类型'],
    capacity: ['项目', '项目组', '存储集群', 'Linux路径', '硬限额', '软限额', '使用量'],
    identity: '研发用户名',
  },
  {
    file: 'src/pages/project/components/ProjectTable.vue',
    progress: ['使用率(%)'],
    secondary: ['存储集群', '存储类型'],
    capacity: ['项目负责人', '限额', '使用量'],
    identity: '项目',
  },
  {
    file: 'src/pages/group/GroupListPage.vue',
    progress: ['硬限额使用率(%)', '软限额使用率(%)'],
    secondary: ['项目组标签'],
    capacity: ['存储集群', '存储类型', '项目', '项目组业务代表', '硬限额', '软限额', '使用量'],
    identity: '项目组名',
  },
  {
    file: 'src/pages/admin/storage-cluster/StorageClusterListPage.vue',
    progress: ['使用率(%)'],
    secondary: ['存储类型', '描述', '协议', 'TLS 校验'],
    capacity: ['限额', '使用量'],
    identity: '集群名称',
  },
  {
    file: 'src/pages/admin/aggregate/AggregateListPage.vue',
    progress: ['使用率(%)'],
    secondary: ['原生类型'],
    capacity: ['存储集群', '存储类型', '限额', '使用量'],
    identity: '容量池名',
  },
  {
    file: 'src/pages/admin/volume/VolumeListPage.vue',
    progress: ['硬限额使用率(%)', '软限额使用率(%)'],
    secondary: ['服务域（SVM / Access Zone）', '原生类型'],
    capacity: ['存储集群', '存储类型', '所属容量池', '状态', '硬限额', '软限额', '使用量'],
    identity: '存储空间名',
  },
  {
    file: 'src/pages/admin/qtree/QtreeListPage.vue',
    progress: ['硬限额使用率(%)', '软限额使用率(%)'],
    secondary: ['style', 'oplocks', '状态'],
    capacity: ['存储集群', '存储类型', '所属存储空间', '硬限额', '软限额', '使用量'],
    identity: 'Qtree（NetApp）名',
  },
];

function source(file) {
  return fs.readFileSync(path.resolve(file), 'utf8');
}

function columns(file) {
  return source(file).match(/<ElTableColumn\b[^>]*>/g) || [];
}

function column(file, label) {
  return columns(file).find((tag) => tag.includes(`label="${label}"`));
}

describe('responsive list column breakpoints', () => {
  it.each([
    [1600, true, true],
    [1200, true, false],
    [900, false, false],
  ])('maps %spx to capacity=%s and secondary=%s', (width, capacity, secondary) => {
    viewportWidth = width;
    const result = useResponsiveTableColumns();

    expect(result.showCapacityColumns.value).toBe(capacity);
    expect(result.showSecondaryColumns.value).toBe(secondary);
  });
});

describe('responsive list column contracts', () => {
  it.each(pageContracts)('$file uses the shared responsive policy', (contract) => {
    const text = source(contract.file);
    expect(text).toContain('useResponsiveTableColumns');

    for (const label of contract.secondary) {
      expect(column(contract.file, label)).toContain('v-if="showSecondaryColumns"');
    }
    for (const label of contract.capacity) {
      expect(column(contract.file, label)).toContain('v-if="showCapacityColumns"');
    }
  });

  it.each(pageContracts)('$file fixes progress and action widths', (contract) => {
    for (const label of contract.progress) {
      expect(column(contract.file, label)).toContain('width="240"');
    }

    expect(columns(contract.file).some((tag) => tag.includes('align="right"') && tag.includes('width="132"'))).toBe(true);
  });

  it.each(pageContracts)('$file keeps its primary identity readable', (contract) => {
    const identity = column(contract.file, contract.identity);

    expect(identity).toContain('show-overflow-tooltip');
    expect(identity).toMatch(/min-width="(140|150|160|180|220)"/);
  });

  it('uses the shared threshold store in the progress component', () => {
    const progress = source('src/components/form/Progress.vue');

    expect(progress).toContain('useStorageAlertThresholds');
    expect(progress).toContain('getQuotaProgressColor');
  });

  it('removes the retired PT manager field and uses project owner terminology', () => {
    const projectTable = source('src/pages/project/components/ProjectTable.vue');
    const projectForm = source('src/pages/project/components/ProjectFormDialog.vue');

    expect(projectTable).not.toContain('PT经理');
    expect(projectForm).not.toContain('PT经理');
    expect(projectTable).toContain('label="项目负责人"');
    expect(projectForm).toContain('label="项目负责人"');
  });
});
