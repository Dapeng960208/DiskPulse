import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { fetchGroups, fetchUsages } = vi.hoisted(() => ({
  fetchGroups: vi.fn(),
  fetchUsages: vi.fn(),
}));

vi.mock('@/api/group-api.js', () => ({
  default: { fetch: fetchGroups },
}));

vi.mock('@/api/storage-usage-api.js', () => ({
  default: { fetch: fetchUsages },
}));

vi.mock('@/components/form/Progress.vue', () => ({
  default: { name: 'Progress', template: '<span />' },
}));

const simpleFormControl = (name) => ({ name, template: '<div><slot /></div>' });

vi.mock('@/components/form/QueryForm.vue', () => ({
  default: {
    name: 'QueryForm',
    emits: ['query', 'reset'],
    template: '<form><slot /><slot name="advanced" /></form>',
  },
}));
vi.mock('@/components/form/RdUserSelect.vue', () => ({ default: simpleFormControl('RdUserSelect') }));
vi.mock('@/components/form/StorageClusterSelect.vue', () => ({ default: simpleFormControl('StorageClusterSelect') }));
vi.mock('@/components/form/GroupTagSelect.vue', () => ({ default: simpleFormControl('GroupTagSelect') }));
vi.mock('@/components/form/GroupSelect.vue', () => ({ default: simpleFormControl('GroupSelect') }));
vi.mock('@/components/form/VolumeSelect.vue', () => ({ default: simpleFormControl('VolumeSelect') }));
vi.mock('@/components/form/QtreeSelect.vue', () => ({ default: simpleFormControl('QtreeSelect') }));

const { default: ProjectGroupsTab } = await import('@/pages/project/components/ProjectGroupsTab.vue');
const { default: ProjectUsagesTab } = await import('@/pages/project/components/ProjectUsagesTab.vue');

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

const createDeferred = () => {
  let resolvePromise;
  let rejectPromise;
  const promise = new Promise((resolve, reject) => {
    resolvePromise = resolve;
    rejectPromise = reject;
  });
  return { promise, resolve: resolvePromise, reject: rejectPromise };
};

const dataTableStub = {
  name: 'DataTable',
  props: ['data', 'loading', 'error', 'pagination'],
  emits: ['update:pagination'],
  template: '<section><slot /></section>',
};

const mountGroupsTab = (projectId = 7) => mount(ProjectGroupsTab, {
  props: { projectId },
  global: {
    stubs: {
      DataTable: dataTableStub,
      ElTableColumn: {
        template: '<div><slot :row="{}" /></div>',
      },
      AccessibleResourceLink: {
        template: '<span><slot /></span>',
      },
      StorageTypeTag: true,
    },
  },
});

const mountUsagesTab = (projectId = 7) => mount(ProjectUsagesTab, {
  props: { projectId },
  global: {
    stubs: {
      DataTable: dataTableStub,
      ElTableColumn: {
        template: '<div><slot :row="{}" /></div>',
      },
      AccessibleResourceLink: {
        template: '<span><slot /></span>',
      },
      Progress: true,
    },
  },
});

async function exerciseOutOfOrderPagination({ fetchMock, mountTab, staleRows, latestRows, staleError }) {
  const oldestRequest = createDeferred();
  const staleRequest = createDeferred();
  const latestRequest = createDeferred();
  fetchMock
    .mockReturnValueOnce(oldestRequest.promise)
    .mockReturnValueOnce(staleRequest.promise)
    .mockReturnValueOnce(latestRequest.promise);

  const wrapper = mountTab();
  const table = wrapper.getComponent({ name: 'DataTable' });
  table.vm.$emit('update:pagination', { page: 2, pageSize: 20 });
  table.vm.$emit('update:pagination', { page: 3, pageSize: 50 });
  expect(fetchMock).toHaveBeenNthCalledWith(1, { project_id: 7, page: 1, size: 20 });
  expect(fetchMock).toHaveBeenNthCalledWith(2, { project_id: 7, page: 2, size: 20 });
  expect(fetchMock).toHaveBeenNthCalledWith(3, { project_id: 7, page: 3, size: 50 });

  staleRequest.resolve({ content: staleRows, total: 62 });
  await flushPromises();
  const whileLatestIsPending = {
    data: table.props('data'),
    total: table.props('pagination').total,
    loading: table.props('loading'),
    error: table.props('error'),
  };

  latestRequest.resolve({ content: latestRows, total: 103 });
  await flushPromises();
  oldestRequest.reject(new Error(staleError));
  await flushPromises();
  const afterOldestFinishesLast = {
    data: table.props('data'),
    total: table.props('pagination').total,
    loading: table.props('loading'),
    error: table.props('error'),
  };
  wrapper.unmount();

  expect({ whileLatestIsPending, afterOldestFinishesLast }).toEqual({
    whileLatestIsPending: {
      data: [],
      total: 0,
      loading: true,
      error: '',
    },
    afterOldestFinishesLast: {
      data: latestRows,
      total: 103,
      loading: false,
      error: '',
    },
  });
}

describe('project detail information architecture', () => {
  beforeEach(() => {
    fetchGroups.mockReset();
    fetchUsages.mockReset();
  });

  it('keeps project resources inside the selected project context', () => {
    const page = source('src/pages/project/ProjectDetailPage.vue');

    expect(page).toContain('ProjectDiskUsage');
    expect(page).toContain('ProjectStorageDistribution');
    expect(page).toContain('ProjectUsagesTab');
    expect(page).toContain('label="项目使用实时"');
    expect(page).toContain('label="存储分布"');
    expect(page).toContain('label="项目组"');
    expect(page).toContain('label="用户目录"');
    expect(page).toContain('label="成员与权限"');
    expect(page).toContain(':attribute-id="projectId"');
    expect(page).toContain(':project-id="projectId"');
    expect(page).toContain('class="project-detail-page__tabs"');
    expect(page).toContain('class="project-detail-page__visual-tab"');
    expect(page).toMatch(/\.project-detail-page \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
  });

  it('loads only the selected project user directories and links to their details', () => {
    const tab = source('src/pages/project/components/ProjectUsagesTab.vue');

    expect(tab).toContain('project_id: props.projectId');
    expect(tab).toContain("name: 'UsagesDetail'");
    expect(tab).toContain('<QueryForm');
    expect(tab).toContain('<RdUserSelect');
    expect(tab).toContain('<StorageClusterSelect');
    expect(tab).toContain('<GroupTagSelect');
    expect(tab).toContain('<GroupSelect');
    expect(tab).toContain('label="项目组标签"');
    expect(tab).toContain('label="软限额使用率(%)"');
    expect(tab).toContain('<DataTable');
    expect(tab).toContain('<AccessibleResourceLink');
    expect(tab).toContain('label="操作"');
    expect(tab).toContain('v-if="canAdjustQuota(row)"');
    expect(tab).toContain('调整额度');
    expect(tab).toContain('<QuotaAdjustmentDialog');
    expect(tab).toContain('fixed="right"');
    expect(tab).toContain('离职账户');
    expect(tab).not.toContain('公共账户');
    expect(tab).not.toContain('label="项目"');
    expect(tab).not.toContain('label="存储类型"');
    expect(tab).not.toContain('StorageTypeTag');
  });

  it('removes the redundant project storage overview while retaining project detail views', () => {
    const listPage = source('src/pages/project/ProjectListPage.vue');
    const detailPage = source('src/pages/project/ProjectDetailPage.vue');

    expect(listPage).not.toContain('<ElTabs');
    expect(listPage).not.toContain('label="项目列表"');
    expect(listPage).not.toContain('项目存储概览图');
    expect(listPage).not.toContain('ProjectDiskUsage');
    expect(detailPage).toContain('label="项目使用实时"');
    expect(detailPage).toContain('label="存储分布"');
  });

  it('loads project groups through a lazy paged tab instead of the detail page mount', () => {
    const page = source('src/pages/project/ProjectDetailPage.vue');
    const tab = source('src/pages/project/components/ProjectGroupsTab.vue');

    expect(page).toContain("const ProjectGroupsTab = defineAsyncComponent(() => import('./components/ProjectGroupsTab.vue'));");
    expect(page).toMatch(/label="项目组"\r?\n\s+name="groups"\r?\n\s+lazy/);
    expect(page).toContain('<ProjectGroupsTab :project-id="projectId" />');
    expect(page).not.toContain("groupApi.fetch({ project_id: projectId.value, page: 1, size: 100 })");

    expect(tab).toContain('project_id: props.projectId');
    expect(tab).toContain('pageSize: 20');
    expect(tab).toContain('<QueryForm');
    expect(tab).toContain('label="项目组名称"');
    expect(tab).toContain('<StorageClusterSelect');
    expect(tab).toContain('<GroupTagSelect');
    expect(tab).toContain('<VolumeSelect');
    expect(tab).toContain('<QtreeSelect');
    expect(tab).toContain('<DataTable');
    expect(tab).toContain('<AccessibleResourceLink');
    expect(tab).toContain('<StorageTypeTag');
  });

  it('requests the selected project groups with server pagination', async () => {
    fetchGroups
      .mockResolvedValueOnce({ content: [{ id: 11, name: '研发组' }], total: 41 })
      .mockResolvedValueOnce({ content: [], total: 41 });

    const wrapper = mountGroupsTab();
    await flushPromises();

    expect(fetchGroups).toHaveBeenNthCalledWith(1, {
      project_id: 7,
      page: 1,
      size: 20,
    });
    const table = wrapper.getComponent({ name: 'DataTable' });
    expect(table.props('pagination')).toMatchObject({ page: 1, pageSize: 20, total: 41 });

    table.vm.$emit('update:pagination', { page: 2, pageSize: 50 });
    await flushPromises();

    expect(fetchGroups).toHaveBeenNthCalledWith(2, {
      project_id: 7,
      page: 2,
      size: 50,
    });
  });

  it('surfaces a project-group loading error without stale pagination', async () => {
    fetchGroups.mockRejectedValueOnce(new Error('network unavailable'));

    const wrapper = mountGroupsTab();
    await flushPromises();

    const table = wrapper.getComponent({ name: 'DataTable' });
    expect(table.props('data')).toEqual([]);
    expect(table.props('pagination')).toMatchObject({ total: 0 });
    expect(table.props('error')).toBe('加载项目组失败，请稍后重试');
  });

  it('keeps only the latest project-group page when requests finish out of order', async () => {
    await exerciseOutOfOrderPagination({
      fetchMock: fetchGroups,
      mountTab: mountGroupsTab,
      staleRows: [{ id: 22, name: '旧分页项目组' }],
      latestRows: [{ id: 33, name: '最新分页项目组' }],
      staleError: 'old group page failed',
    });
  });

  it('keeps only the latest user-directory page when requests finish out of order', async () => {
    await exerciseOutOfOrderPagination({
      fetchMock: fetchUsages,
      mountTab: mountUsagesTab,
      staleRows: [{ id: 122, linux_path: '/old/page' }],
      latestRows: [{ id: 133, linux_path: '/latest/page' }],
      staleError: 'old usage page failed',
    });
  });
});
