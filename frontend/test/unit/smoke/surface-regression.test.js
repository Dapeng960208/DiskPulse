import { defineComponent, h, ref } from 'vue';
import { shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';
import { createPinia } from 'pinia';
import { RouterLinkStub, commonStubs } from '../../helpers/mount';

const { requestStub, routerPush } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  requestStub: {
    get: vi.fn(() => Promise.resolve({ data: { content: [], data: [], result: {}, info: {}, total: 0 } })),
    post: vi.fn(() => Promise.resolve({ data: { result: {} } })),
    put: vi.fn(() => Promise.resolve({ data: { result: {} } })),
    patch: vi.fn(() => Promise.resolve({ data: { result: {} } })),
    delete: vi.fn(() => Promise.resolve({ data: { result: {} } })),
    head: vi.fn(() => Promise.resolve({ config: { headers: {} }, request: { responseURL: 'https://example.com/file' } })),
    all: vi.fn(),
    spread: vi.fn(),
  },
}));

vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    on: vi.fn(),
    off: vi.fn(),
    showLoading: vi.fn(),
    hideLoading: vi.fn(),
  })),
  graphic: {
    LinearGradient: class LinearGradient {},
  },
}));

vi.mock('@element-plus/icons-vue', () => ({
  User: {},
  Lock: {},
}));

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router');

  return {
    ...actual,
    useRoute: () => ({
      matched: [{ name: 'Dashboard', meta: { title: 'Dashboard' } }],
      params: { id: '1' },
      query: {},
      path: '/',
      meta: {},
    }),
    useRouter: () => ({
      push: routerPush,
      replace: routerPush,
      getRoutes: () => [
        {
          name: 'Dashboard',
          path: '/',
          meta: {
            isRoot: true,
            title: 'Dashboard',
            icon: 'i-ri-dashboard-2-line',
          },
          children: [],
        },
      ],
    }),
  };
});

vi.mock('@/composables/query', () => ({
  useQuery: (request, initialValue = []) => {
    const result = ref(initialValue);
    return {
      result,
      querying: ref(false),
      query: vi.fn(async () => {
        result.value = await request();
        return result.value;
      }),
    };
  },
  useQueryParams: (provider) => {
    const queryParams = ref(provider());

    return {
      queryParams,
      reset: vi.fn(() => {
        queryParams.value = provider();
      }),
    };
  },
}));

vi.mock('@/composables/dialog', () => ({
  useDialog: () => ({
    dialogRef: ref(null),
    visible: ref(false),
    open: vi.fn(),
    close: vi.fn(),
  }),
}));

vi.mock('@/api/support/base-request', () => ({
  default: requestStub,
}));

vi.mock('@/api/support/auth-request', () => ({
  default: requestStub,
}));

vi.mock('@/composables/form', () => ({
  useForm: (initialModel) => ({
    formRef: ref({ validate: vi.fn(() => Promise.resolve(true)) }),
    mode: ref('create'),
    model: ref(initialModel()),
    modelRules: ref({}),
    submitting: ref(false),
    edit: vi.fn(),
    submit: vi.fn(),
    toggleSubmitting: vi.fn(),
  }),
}));

vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => ({
    id: 1,
    avatarUrl: 'avatar.png',
    displayName: 'DiskPulse User',
    roleCodes: ['diskpulse:admin'],
    permissions: [],
    extensionAttributes: {},
    setCurrentUser: vi.fn(),
    $reset: vi.fn(),
  }),
}));

vi.mock('@/stores/app-settings', () => ({
  useAppSettings: () => ({
    asideCollapsed: false,
    theme: 'light',
    toggleAsideCollapsed: vi.fn(),
    toggleTheme: vi.fn(() => true),
  }),
}));

vi.mock('@/utils/authorization', async () => {
  const actual = await vi.importActual('@/utils/authorization');

  return {
    ...actual,
    hasRole: vi.fn(() => true),
    hasAnyRole: vi.fn(() => true),
    hasAllRoles: vi.fn(() => true),
    hasPermission: vi.fn(() => true),
    hasAnyPermission: vi.fn(() => true),
    isAuthenticated: vi.fn(() => true),
    removeToken: vi.fn(),
    setToken: vi.fn(),
  };
});

const surfaceModules = {
  ...import.meta.glob('/src/common/charts/*.vue', { eager: true }),
  ...import.meta.glob('/src/components/form/*.vue', { eager: true }),
  ...import.meta.glob('/src/layouts/*.vue', { eager: true }),
  ...import.meta.glob('/src/layouts/components/*.vue', { eager: true }),
  ...import.meta.glob('/src/pages/**/*.vue', { eager: true }),
};

const skippedPaths = new Set([
  '/src/pages/error/NotFoundPage.vue',
  '/src/pages/error/UnauthorizedPage.vue',
  '/src/pages/project/ProjectDetailPage.vue',
  '/src/pages/group/GroupDetailPage.vue',
  '/src/pages/usage/UsageDetailPage.vue',
  '/src/pages/admin/aggregate/AggregateDetailPage.vue',
  '/src/pages/admin/qtree/QtreeDetailPage.vue',
  '/src/pages/admin/volume/VolumeDetailPage.vue',
]);

function resolvePropValue(path, name, definition) {
  if (name === 'apiType') return 'project';
  if (name === 'attributeId') return 1;
  if (name === 'label') return 'Label';
  if (name === 'option') {
    return {
      label: 'Menu',
      path: '/',
      icon: 'i-ri-dashboard-2-line',
      children: [],
      isVisible: () => true,
      isActive: () => false,
    };
  }
  if (name === 'type') {
    if (path.includes('AccountSelect.vue')) return 'employee';
    if (path.includes('DomainGroupSelect.vue')) return 'distribution';

    return undefined;
  }
  if (name === 'to') return '/';
  if (name === 'title') return 'Title';
  if (name === 'tip') return 'Tip';
  if (name === 'src') return 'avatar.png';
  if (name === 'resourceType') return 'group';
  if (name === 'modelValue') {
    const type = Array.isArray(definition?.type) ? definition.type[0] : definition?.type;

    if (type === Number) return 1;
    if (type === String) return '';

    return [];
  }
  if (name === 'data') {
    if (path.includes('BarStackChart.vue')) {
      return [[1, 2], [3, 4]];
    }

    if (path.includes('LineCharts.vue') || path.includes('AnimatedTextChart.vue')) {
      return [{ time: '2024-01-01 00:00:00', value: 1 }];
    }

    if (path.includes('DiskUsage.vue') || path.includes('PieCharts.vue') || path.includes('StoragePieAndLineCharts.vue')) {
      return [{ name: 'A', value: 1 }];
    }

    if (path.includes('MultipleLineCharts.vue')) {
      return { seriesA: [{ time: '2024-01-01 00:00:00', value: 1 }] };
    }

    return [];
  }
  if (name === 'pagination') {
    return {
      page: 1,
      pageSize: 20,
      total: 0,
      pageSizes: [20],
      showJumper: true,
    };
  }
  if (name === 'result') return {};
  if (name === 'height') return '300px';
  if (name === 'width') return '300px';

  const type = Array.isArray(definition?.type) ? definition.type[0] : definition?.type;

  if (type === String) return '';
  if (type === Number) return 1;
  if (type === Boolean) return false;
  if (type === Array) return [];
  if (type === Object) return {};

  return undefined;
}

function buildProps(component, path) {
  const props = {};
  const definitions = component.props;

  if (!definitions || Array.isArray(definitions)) {
    return props;
  }

  Object.entries(definitions).forEach(([name, definition]) => {
    const value = resolvePropValue(path, name, definition);

    if (value !== undefined) {
      props[name] = value;
    }
  });

  return props;
}

function createEmptyStub(name, tag = 'div') {
  return defineComponent({
    name,
    setup(_, { attrs }) {
      return () => h(tag, attrs);
    },
  });
}

const surfaceStubs = {
  ...commonStubs,
  RouterLink: RouterLinkStub,
  RouterView: createEmptyStub('RouterView'),
  ElAlert: createEmptyStub('ElAlert'),
  ElAside: createEmptyStub('ElAside'),
  ElBreadcrumb: createEmptyStub('ElBreadcrumb'),
  ElBreadcrumbItem: createEmptyStub('ElBreadcrumbItem'),
  ElButton: createEmptyStub('ElButton', 'button'),
  ElCard: createEmptyStub('ElCard'),
  ElCascader: createEmptyStub('ElCascader'),
  ElCheckbox: createEmptyStub('ElCheckbox'),
  ElCol: createEmptyStub('ElCol'),
  ElContainer: createEmptyStub('ElContainer'),
  ElDatePicker: createEmptyStub('ElDatePicker'),
  ElDescriptions: createEmptyStub('ElDescriptions'),
  ElDescriptionsItem: createEmptyStub('ElDescriptionsItem'),
  ElDialog: createEmptyStub('ElDialog'),
  ElDropdown: createEmptyStub('ElDropdown'),
  ElDropdownItem: createEmptyStub('ElDropdownItem'),
  ElDropdownMenu: createEmptyStub('ElDropdownMenu'),
  ElForm: createEmptyStub('ElForm', 'form'),
  ElFormItem: createEmptyStub('ElFormItem'),
  ElHeader: createEmptyStub('ElHeader'),
  ElInput: createEmptyStub('ElInput', 'input'),
  ElLink: createEmptyStub('ElLink', 'a'),
  ElMain: createEmptyStub('ElMain'),
  ElMenu: createEmptyStub('ElMenu'),
  ElMenuItem: createEmptyStub('ElMenuItem'),
  ElOption: createEmptyStub('ElOption'),
  ElPagination: createEmptyStub('ElPagination'),
  ElRow: createEmptyStub('ElRow'),
  ElScrollbar: createEmptyStub('ElScrollbar'),
  ElSelect: createEmptyStub('ElSelect', 'select'),
  ElSpace: createEmptyStub('ElSpace'),
  ElSubMenu: createEmptyStub('ElSubMenu'),
  ElSwitch: createEmptyStub('ElSwitch'),
  ElTable: createEmptyStub('ElTable'),
  ElTableColumn: createEmptyStub('ElTableColumn'),
  ElTag: createEmptyStub('ElTag'),
  ElTransfer: createEmptyStub('ElTransfer'),
  ElTreeSelect: createEmptyStub('ElTreeSelect'),
  TransitionGroup: createEmptyStub('TransitionGroup'),
};

describe('surface regression smoke', () => {
  const entries = Object.entries(surfaceModules).filter(([path]) => !skippedPaths.has(path));

  it.each(entries)('mounts %s', async (path, module) => {
    const component = module.default;

    expect(component).toBeTruthy();

    const wrapper = shallowMount(component, {
      props: buildProps(component, path),
      slots: {
        default: '<div>default</div>',
        advanced: '<div>advanced</div>',
        exportExcel: '<div>export</div>',
        extraDescriptions: '<div>extra</div>',
      },
      global: {
        plugins: [createPinia()],
        stubs: surfaceStubs,
        renderStubDefaultSlot: false,
        directives: {
          loading: () => undefined,
        },
        mocks: {
          $route: {
            matched: [{ name: 'Dashboard', meta: { title: 'Dashboard' } }],
          },
          $router: {
            push: routerPush,
          },
        },
      },
    });

    expect(wrapper.exists()).toBe(true);
  });
});
