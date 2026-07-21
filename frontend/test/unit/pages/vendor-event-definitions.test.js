import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { ElMessage } from 'element-plus';
import { vi } from 'vitest';
import VendorEventDefinitionPage from '@/pages/admin/vendor-event-definition/VendorEventDefinitionPage.vue';

const vendorEventDefinitionApi = vi.hoisted(() => ({
  fetch: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  deleteById: vi.fn(),
  discover: vi.fn(),
}));

vi.mock('@/api/vendor-event-definition-api.js', () => ({ default: vendorEventDefinitionApi }));

const passthrough = (name, tag = 'div') => defineComponent({
  name,
  inheritAttrs: false,
  setup(_, { attrs, slots }) {
    return () => h(tag, attrs, [slots.default?.(), slots.footer?.()]);
  },
});

const DataTable = defineComponent({
  name: 'DataTable',
  props: {
    data: { type: Array, default: () => [] },
    pagination: { type: Object, default: () => ({}) },
  },
  emits: ['update:pagination'],
  setup(props, { slots }) {
    return () => h('div', { 'data-testid': 'event-association-table' }, [
      JSON.stringify(props.data),
      slots.default?.(),
    ]);
  },
});

const TableColumn = defineComponent({
  name: 'ElTableColumn',
  setup(_, { slots }) {
    const row = {
      id: 1,
      storage_type: 'netapp',
      event_code: 'secd.authsys.lookup.failed',
      association_type: 'fault_log',
      title_zh: '认证服务查询失败',
      review_status: 'reviewed',
      is_active: true,
    };
    return () => h('div', [slots.header?.(), slots.default?.({ row })]);
  },
});

const QueryForm = defineComponent({
  name: 'QueryForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', [slots.default?.(), slots.actions?.()]);
  },
});

async function mountPage() {
  const wrapper = shallowMount(VendorEventDefinitionPage, {
    global: {
      stubs: {
        DataTable,
        QueryForm,
        TableActionButton: passthrough('TableActionButton', 'button'),
        ElButton: passthrough('ElButton', 'button'),
        ElDialog: passthrough('ElDialog'),
        ElForm: passthrough('ElForm', 'form'),
        ElFormItem: passthrough('ElFormItem'),
        ElInput: passthrough('ElInput', 'input'),
        ElSelect: passthrough('ElSelect', 'select'),
        ElOption: passthrough('ElOption', 'option'),
        ElTableColumn: TableColumn,
        ElTag: passthrough('ElTag'),
      },
    },
  });
  await flushPromises();
  return wrapper;
}

describe('VendorEventDefinitionPage', () => {
  beforeEach(() => {
    vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    vendorEventDefinitionApi.fetch.mockResolvedValue({
      content: [{
        id: 1,
        storage_type: 'netapp',
        event_code: 'secd.authsys.lookup.failed',
        association_type: 'fault_log',
        title_zh: '认证服务查询失败',
        description_zh: '名称服务或认证后端查询失败。',
        official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems/search.html',
        is_active: true,
      }],
      total: 1,
    });
    vendorEventDefinitionApi.discover.mockResolvedValue({ created: 2, existing: 7, reconciled_incidents: 2 });
    vendorEventDefinitionApi.create.mockResolvedValue({ id: 2 });
    vendorEventDefinitionApi.update.mockResolvedValue({ id: 1 });
    vendorEventDefinitionApi.deleteById.mockResolvedValue(undefined);
  });

  afterEach(() => vi.restoreAllMocks());

  it('lists all maintained event associations with explicit semantic fields', async () => {
    const wrapper = await mountPage();

    expect(vendorEventDefinitionApi.fetch).toHaveBeenCalledWith(expect.objectContaining({ page: 1, size: 20 }));
    expect(wrapper.findComponent({ name: 'DataTable' }).exists()).toBe(true);
    expect(wrapper.findComponent({ name: 'DataTable' }).props('data')).toEqual([
      expect.objectContaining({
        storage_type: 'netapp',
        event_code: 'secd.authsys.lookup.failed',
        association_type: 'fault_log',
        title_zh: '认证服务查询失败',
      }),
    ]);
    expect(wrapper.find('[data-testid="event-association-create"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="event-association-edit-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="event-association-delete-1"]').exists()).toBe(true);
  });

  it('discovers collected codes and reconciles legacy misclassified incidents', async () => {
    const wrapper = await mountPage();

    await wrapper.get('[data-testid="event-association-sync"]').trigger('click');
    await flushPromises();

    expect(vendorEventDefinitionApi.discover).toHaveBeenCalledTimes(1);
    expect(ElMessage.success).toHaveBeenCalledWith('新增 2 个代码，已保留 7 个；修复 2 个历史误分类事件');
    expect(vendorEventDefinitionApi.fetch).toHaveBeenCalledTimes(2);
  });
});
