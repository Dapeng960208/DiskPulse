import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineComponent, h, reactive, ref } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const route = reactive({
  params: { id: '7' },
  query: {},
});
const routerReplace = vi.fn(() => Promise.resolve());

const projectStorageEnvironmentApi = {
  fetchByProject: vi.fn(),
  fetchSummaryById: vi.fn(),
  fetchStorageRealTimeDataById: vi.fn(),
};
const groupApi = {
  fetch: vi.fn(),
};
const alertApi = {
  fetch: vi.fn(),
};

function componentStub(name) {
  return defineComponent({
    name,
    setup() {
      return () => h('div');
    },
  });
}

vi.mock('vue-router', async (importOriginal) => ({
  ...await importOriginal(),
  useRoute: () => route,
  useRouter: () => ({ replace: routerReplace }),
}));

vi.mock('@/api/project-storage-environment-api', () => ({
  default: projectStorageEnvironmentApi,
}));
vi.mock('@/api/support/base-request', () => ({ default: {} }));
vi.mock('@/api/support/auth-request', () => ({ default: {} }));
vi.mock('@/api/group-api.js', () => ({ default: groupApi }));
vi.mock('@/api/alert-api.js', () => ({ default: alertApi }));
vi.mock('@/api/qtree-api.js', () => ({ default: {} }));
vi.mock('@/api/volume-api.js', () => ({ default: {} }));
vi.mock('@/api/aggregate-api.js', () => ({ default: {} }));
vi.mock('@/api/project-api.js', () => ({ default: {} }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: {} }));

vi.mock('@/common/charts/MultipleLineCharts.vue', () => ({
  default: componentStub('MultipleLineCharts'),
}));
vi.mock('@/common/charts/LineCharts.vue', () => ({ default: componentStub('LineCharts') }));
vi.mock('@/common/charts/LoadingCharts.vue', () => ({ default: componentStub('LoadingCharts') }));
vi.mock('@/common/charts/AnimatedTextChart.vue', () => ({
  default: componentStub('AnimatedTextChart'),
}));
vi.mock('@/components/form/QueryForm.vue', () => ({ default: componentStub('QueryForm') }));
vi.mock('@/components/form/QtreeSelect.vue', () => ({ default: componentStub('QtreeSelect') }));
vi.mock('@/components/form/VolumeSelect.vue', () => ({ default: componentStub('VolumeSelect') }));
vi.mock('@/components/form/AggregateSelect.vue', () => ({ default: componentStub('AggregateSelect') }));
vi.mock('@/components/form/ProjectSelect.vue', () => ({ default: componentStub('ProjectSelect') }));
vi.mock('@/components/form/StorageUsageSelect.vue', () => ({
  default: componentStub('StorageUsageSelect'),
}));
vi.mock('@/components/form/GroupSelect.vue', () => ({ default: componentStub('GroupSelect') }));
vi.mock('@/components/form/RdUserSelect.vue', () => ({ default: componentStub('RdUserSelect') }));
vi.mock('@/pages/project/components/ProjectStorageEnvironmentTable.vue', () => ({
  default: componentStub('ProjectStorageEnvironmentTable'),
}));

vi.mock('@/composables/query', () => ({
  useQueryParams: (defaultProvider) => {
    const queryParams = ref(defaultProvider());
    return {
      queryParams,
      reset: vi.fn(() => {
        queryParams.value = defaultProvider();
      }),
    };
  },
  useQuery: (request, initialValue = []) => {
    const result = ref(initialValue);
    const querying = ref(false);
    const query = vi.fn(async () => {
      querying.value = true;
      try {
        result.value = await request();
      } catch {
        result.value = initialValue;
      } finally {
        querying.value = false;
      }
    });
    return { result, querying, query };
  },
}));

const ElTabsStub = defineComponent({
  name: 'ElTabs',
  props: {
    modelValue: {
      type: [String, Number],
      default: null,
    },
  },
  emits: ['update:modelValue'],
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const ElTabPaneStub = defineComponent({
  name: 'ElTabPane',
  props: {
    label: String,
    name: {
      type: [String, Number],
      default: null,
    },
  },
  setup(props, { slots }) {
    return () => h('section', { 'data-environment-id': props.name }, slots.default?.());
  },
});

const ElEmptyStub = defineComponent({
  name: 'ElEmpty',
  props: {
    description: String,
  },
  setup(props) {
    return () => h('div', props.description);
  },
});

const detailStubs = {
  ElEmpty: ElEmptyStub,
  ElTabs: ElTabsStub,
  ElTabPane: ElTabPaneStub,
};

const environments = [
  {
    id: 11,
    project_id: 7,
    name: 'netapp-primary',
    is_active: true,
    storage_cluster: { id: 101, name: 'netapp-1', storage_type: 'netapp' },
  },
  {
    id: 12,
    project_id: 7,
    name: 'disabled-environment',
    is_active: false,
    storage_cluster: { id: 102, name: 'isilon-disabled', storage_type: 'isilon' },
  },
  {
    id: 13,
    project_id: 7,
    name: 'isilon-secondary',
    is_active: true,
    storage_cluster: { id: 103, name: 'isilon-1', storage_type: 'isilon' },
  },
];

async function mountProjectDetail(query = {}, response = environments) {
  route.params = { id: '7' };
  route.query = { ...query };
  projectStorageEnvironmentApi.fetchByProject.mockResolvedValue({
    content: response,
    total: response.length,
  });
  const { default: ProjectDetailPage } = await import(
    '@/pages/project/ProjectDetailPage.vue'
  );
  const wrapper = shallowMount(ProjectDetailPage, {
    global: { stubs: detailStubs },
  });
  await flushPromises();
  return wrapper;
}

function expectEnvironmentLoads(environmentId) {
  expect(projectStorageEnvironmentApi.fetchSummaryById).toHaveBeenCalledWith(environmentId);
  expect(groupApi.fetch).toHaveBeenCalledWith(expect.objectContaining({
    project_environment_id: environmentId,
  }));
}

describe('project environment workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    projectStorageEnvironmentApi.fetchSummaryById.mockResolvedValue({
      id: 11,
      used: 40,
      limit: 100,
      use_ratio: 40,
    });
    projectStorageEnvironmentApi.fetchStorageRealTimeDataById.mockResolvedValue({
      info: { id: 11, name: 'netapp-primary', used: 40, limit: 100, use_ratio: 40 },
      data: [],
    });
    groupApi.fetch.mockResolvedValue({ content: [], total: 0 });
    alertApi.fetch.mockResolvedValue({ content: [] });
  });

  it('renders project storage environment overview fields in the project list', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/project/components/ProjectTable.vue'),
      'utf8',
    );

    [
      'storage_environment_count',
      'active_storage_environment_count',
      'storage_cluster_types',
      'storage_environment_status_counts',
      'pending',
      'success',
      'failed',
      'inactive',
    ].forEach((field) => expect(source).toContain(field));
  });

  it('keeps a valid shared environment query and loads only that environment', async () => {
    const wrapper = await mountProjectDetail({ environment_id: '13' });

    expect(projectStorageEnvironmentApi.fetchByProject).toHaveBeenCalledWith(7, {
      page: 1,
      size: 100,
    });
    expect(routerReplace).not.toHaveBeenCalled();
    expectEnvironmentLoads(13);
    const realtime = wrapper.findComponent({ name: 'RealTimePage' });
    expect(realtime.props('apiType')).toBe('project-environment');
    expect(realtime.props('attributeId')).toBe(13);
    expect(wrapper.findAllComponents(ElTabPaneStub).map(
      (tab) => Number(tab.props('name')),
    )).toEqual([11, 13]);
  });

  it.each([
    ['missing', {}],
    ['invalid', { environment_id: 'not-an-id' }],
    ['another project', { environment_id: '99' }],
    ['inactive', { environment_id: '12' }],
  ])('normalizes a %s environment query to the first active environment', async (_, query) => {
    const wrapper = await mountProjectDetail({ view: 'workspace', ...query });

    expect(routerReplace).toHaveBeenCalledWith(expect.objectContaining({
      query: {
        view: 'workspace',
        environment_id: '11',
      },
    }));
    expectEnvironmentLoads(11);
    expect(wrapper.findComponent({ name: 'RealTimePage' }).props('attributeId')).toBe(11);
  });

  it('clears the environment query and renders an empty state when none are active', async () => {
    const wrapper = await mountProjectDetail(
      { view: 'workspace', environment_id: '12' },
      [environments[1]],
    );

    expect(routerReplace).toHaveBeenCalledWith(expect.objectContaining({
      query: { view: 'workspace' },
    }));
    expect(wrapper.text()).toContain('暂无启用的存储环境');
    expect(wrapper.findComponent({ name: 'RealTimePage' }).exists()).toBe(false);
    expect(projectStorageEnvironmentApi.fetchSummaryById).not.toHaveBeenCalled();
    expect(groupApi.fetch).not.toHaveBeenCalled();
  });

  it('switches the environment tab and reloads only the selected environment workspace', async () => {
    const wrapper = await mountProjectDetail({ environment_id: '11' });
    projectStorageEnvironmentApi.fetchSummaryById.mockClear();
    groupApi.fetch.mockClear();
    routerReplace.mockClear();

    const tabs = wrapper.findComponent(ElTabsStub);
    expect(tabs.exists()).toBe(true);
    tabs.vm.$emit('update:modelValue', 13);
    await flushPromises();

    expect(routerReplace).toHaveBeenCalledWith(expect.objectContaining({
      query: { environment_id: '13' },
    }));
    expectEnvironmentLoads(13);
    expect(projectStorageEnvironmentApi.fetchSummaryById).toHaveBeenCalledTimes(1);
    expect(groupApi.fetch).toHaveBeenCalledTimes(1);
    expect(wrapper.findComponent({ name: 'RealTimePage' }).props('attributeId')).toBe(13);
  });

  it('supports project-environment realtime requests', async () => {
    const { default: RealTimePage } = await import('@/pages/common/RealTimePage.vue');
    shallowMount(RealTimePage, {
      props: {
        apiType: 'project-environment',
        label: '存储环境',
        attributeId: 13,
      },
    });
    await flushPromises();

    expect(projectStorageEnvironmentApi.fetchStorageRealTimeDataById).toHaveBeenCalledWith(
      13,
      expect.objectContaining({ indicator: 'used' }),
    );
  });
});
