import { mount, shallowMount } from '@vue/test-utils';
import { defineComponent, h } from 'vue';
import { describe, expect, it, vi } from 'vitest';
import { commonStubs } from '../helpers/mount';

vi.mock('@/stores/app-settings', () => ({
  useAppSettings: () => ({
    theme: 'light',
    asideCollapsed: false,
    toggleTheme: vi.fn(() => true),
    toggleAsideCollapsed: vi.fn(),
  }),
}));

vi.mock('@/stores/breadcrumbs', () => ({
  useBreadcrumbs: () => ({
    detailBreadcrumbFor: vi.fn(() => []),
    detailTitleFor: vi.fn(() => ''),
    setDetailBreadcrumb: vi.fn(),
    setDetailTitle: vi.fn(),
  }),
}));

vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router');

  return {
    ...actual,
    useRoute: () => ({
      matched: [{ name: 'Dashboard', meta: { title: '概览' } }],
      name: 'Dashboard',
    }),
  };
});

vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => ({
    avatarUrl: '',
    displayName: '研发用户',
    $reset: vi.fn(),
  }),
}));

vi.mock('@/utils/authorization', () => ({
  isAuthenticated: () => true,
  removeToken: vi.fn(),
  hasRole: () => true,
}));

vi.mock('@/api/users-api', () => ({
  default: {
    logout: vi.fn(() => Promise.resolve()),
  },
}));

vi.mock('@/utils', () => ({
  toLoginPage: vi.fn(),
}));

vi.mock('@/assets/logo.png', () => ({
  default: '/logo.png',
}));

vi.mock('element-plus', () => ({
  ElAside: commonStubs.ElAside || commonStubs.ElCard,
  ElBreadcrumb: commonStubs.ElBreadcrumb || commonStubs.ElCard,
  ElBreadcrumbItem: commonStubs.ElBreadcrumbItem || commonStubs.ElCard,
  ElButton: commonStubs.ElButton,
  ElCard: commonStubs.ElCard,
  ElContainer: commonStubs.ElContainer || commonStubs.ElCard,
  ElDropdown: commonStubs.ElDropdown || commonStubs.ElCard,
  ElDropdownItem: commonStubs.ElDropdownItem || commonStubs.ElCard,
  ElDropdownMenu: commonStubs.ElDropdownMenu || commonStubs.ElCard,
  ElFooter: commonStubs.ElFooter || commonStubs.ElCard,
  ElHeader: commonStubs.ElHeader || commonStubs.ElCard,
  ElMain: commonStubs.ElMain || commonStubs.ElCard,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()) },
  ElPagination: commonStubs.ElPagination,
  ElScrollbar: commonStubs.ElScrollbar || commonStubs.ElCard,
  ElSpace: commonStubs.ElSpace || commonStubs.ElCard,
  ElTable: commonStubs.ElTable,
}));

const RouterViewStub = defineComponent({
  name: 'RouterView',
  props: {
    name: {
      type: String,
      default: 'default',
    },
  },
  setup(_, { slots }) {
    return () => (slots.default ? slots.default({ Component: null, route: { name: 'Dashboard', meta: {} } }) : h('div'));
  },
});

describe('frontend audit implementation contract', () => {
  it('renders the aside collapse trigger as an accessible stateful button', async () => {
    const { default: AppLayout } = await import('@/layouts/AppLayout.vue');

    const wrapper = shallowMount(AppLayout, {
      props: { showAside: true },
      global: {
        stubs: {
          ...commonStubs,
          AppHeader: true,
          AppFooter: true,
          RouteMenu: true,
          RouterView: RouterViewStub,
        },
        mocks: {
          $route: {
            matched: [{ name: 'Dashboard', meta: { title: '概览' } }],
          },
        },
      },
    });

    const button = wrapper.get('[data-testid="aside-collapse-toggle"]');

    expect(button.element.tagName).toBe('BUTTON');
    expect(button.attributes('aria-expanded')).toBe('true');
    expect(button.attributes('aria-controls')).toBe('app-aside');
    expect(button.attributes('aria-label')).toBe('收起侧边导航');
  });

  it('renders the application footer at the compact 40px height by default', async () => {
    const { default: AppFooter } = await import('@/layouts/components/AppFooter.vue');

    const wrapper = shallowMount(AppFooter);

    expect(wrapper.props('height')).toBe('40px');
  });

  it('keeps the application footer outside the scrollable main content', async () => {
    const { default: AppLayout } = await import('@/layouts/AppLayout.vue');
    const { default: AppFooter } = await import('@/layouts/components/AppFooter.vue');

    const wrapper = shallowMount(AppLayout, {
      props: { showAside: false },
      global: {
        stubs: {
          ...commonStubs,
          AppHeader: true,
          AppFooter: true,
          RouteMenu: true,
          RouterView: RouterViewStub,
        },
        mocks: {
          $route: {
            matched: [{ name: 'Dashboard', meta: { title: '概览' } }],
          },
        },
      },
    });

    const footer = wrapper.getComponent(AppFooter);
    const workspace = wrapper.get('.app-layout__workspace');
    const scrollbar = wrapper.get('.app-main__scrollbar');

    expect(wrapper.find('#app-aside').exists()).toBe(false);
    expect(workspace.element.lastElementChild).toBe(footer.element);
    expect(scrollbar.element.contains(footer.element)).toBe(false);
    expect(footer.props('height')).toBe('40px');
  });

  it('keeps the theme switch accessible and silent when view transitions are unavailable', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const { default: ThemeSwitch } = await import('@/components/basic/ThemeSwitch.vue');

    const wrapper = mount(ThemeSwitch);
    const button = wrapper.get('button');

    expect(button.attributes('aria-label')).toBe('切换到暗色模式');
    expect(button.attributes('aria-pressed')).toBe('false');

    await button.trigger('click');

    expect(consoleError).not.toHaveBeenCalled();
  });

  it('gives GridContainer a stable tail slot class and responsive placement hook', async () => {
    const { default: GridContainer } = await import('@/components/basic/GridContainer.vue');

    const wrapper = shallowMount(GridContainer, {
      slots: {
        default: '<div>筛选项</div>',
        tail: '<button>搜索</button>',
      },
    });

    const tail = wrapper.get('.grid-tail');

    expect(tail.attributes('style')).toContain('--grid-tail-column');
    expect(wrapper.get('.grid-container').attributes('style')).toContain('--grid-min-column-width');
  });

  it('supports DataTable density and user-visible error state', async () => {
    const { default: DataTable } = await import('@/components/data/DataTable.vue');

    const wrapper = shallowMount(DataTable, {
      props: {
        data: [],
        density: 'compact',
        error: '数据加载失败',
      },
      global: {
        stubs: commonStubs,
        directives: {
          loading: () => undefined,
        },
      },
    });

    expect(wrapper.classes()).toContain('data-table-card--compact');
    expect(wrapper.text()).toContain('数据加载失败');
  });
});
