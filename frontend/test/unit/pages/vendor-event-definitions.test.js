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

vi.mock('@/api/admin/vendor-event-definition-api.js', () => ({ default: vendorEventDefinitionApi }));

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
      description_zh: '名称服务或认证后端查询失败。',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems-9181/',
      version_scope: 'ONTAP 9.18.1',
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

async function fillDefinitionForm(wrapper, {
  storageType = 'netapp',
  associationType = 'unknown',
  reviewStatus = 'pending',
  officialReferenceUrl = '',
  versionScope = '',
} = {}) {
  await wrapper.get('[data-testid="event-association-create"]').trigger('click');
  const dialog = wrapper.findComponent({ name: 'ElDialog' });
  const inputs = dialog.findAllComponents({ name: 'ElInput' });
  const selects = dialog.findAllComponents({ name: 'ElSelect' });

  await inputs[0].vm.$emit('update:modelValue', 'test.vendor.event');
  await inputs[1].vm.$emit('update:modelValue', '测试厂商事件');
  await inputs[2].vm.$emit('update:modelValue', '用于验证审核边界的中文说明。');
  await inputs[3].vm.$emit('update:modelValue', officialReferenceUrl);
  await inputs[4].vm.$emit('update:modelValue', versionScope);
  await selects[0].vm.$emit('update:modelValue', storageType);
  await selects[1].vm.$emit('update:modelValue', associationType);
  await selects[3].vm.$emit('update:modelValue', reviewStatus);

  return dialog.findAllComponents({ name: 'ElButton' })
    .find((button) => button.text() === '保存');
}

describe('VendorEventDefinitionPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(ElMessage, 'success').mockImplementation(() => {});
    vi.spyOn(ElMessage, 'error').mockImplementation(() => {});
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

  it.each([
    {
      associationType: 'unknown',
      officialReferenceUrl: 'https://docs.netapp.com/us-en/ontap-ems-9181/',
      versionScope: 'ONTAP 9.18.1',
      message: '已审核定义必须选择明确的关联类型',
    },
    {
      associationType: 'fault_log',
      officialReferenceUrl: 'http://docs.example.com/event',
      versionScope: 'ONTAP 9.18.1',
      message: '已审核定义必须填写有效的官方 HTTPS 参考地址',
    },
    {
      associationType: 'fault_log',
      officialReferenceUrl: 'https://docs.netapp.com/us-en/ontap-ems-9181/',
      versionScope: '',
      message: '已审核定义必须填写适用版本',
    },
  ])('blocks a reviewed definition without complete evidence: $message', async (formState) => {
    const wrapper = await mountPage();
    const saveButton = await fillDefinitionForm(wrapper, {
      ...formState,
      reviewStatus: 'reviewed',
    });

    await saveButton.trigger('click');
    await flushPromises();

    expect(ElMessage.error).toHaveBeenCalledWith(formState.message);
    expect(vendorEventDefinitionApi.create).not.toHaveBeenCalled();
  });

  it('allows a pending unknown definition without official evidence', async () => {
    const wrapper = await mountPage();
    const saveButton = await fillDefinitionForm(wrapper);

    await saveButton.trigger('click');
    await flushPromises();

    expect(vendorEventDefinitionApi.create).toHaveBeenCalledWith(expect.objectContaining({
      association_type: 'unknown',
      official_reference_url: null,
      version_scope: null,
      review_status: 'pending',
    }));
  });

  it.each([
    'http://docs.netapp.com/us-en/ontap-ems/events.html',
    'https://docs.example.com/vendor-events',
    'https://evilnetapp.com/vendor-events',
    'https://operator@docs.netapp.com/us-en/ontap-ems/events.html',
    'https://docs.netapp.com:443/us-en/ontap-ems/events.html',
    'https://docs.netapp.com./us-en/ontap-ems/events.html',
    'https://docs.netapp.com/us-en/ontap-ems/events@v1.html',
    'https://www.dell.com/support/manuals/en-us/powerscale-onefs/events',
    ' https://docs.netapp.com/us-en/ontap-ems/events.html',
    'https://docs.netapp.com/us-en/ontap-ems/events.html ',
  ])('rejects an unsafe non-empty official URL while the definition is pending: %s', async (officialReferenceUrl) => {
    const wrapper = await mountPage();
    const saveButton = await fillDefinitionForm(wrapper, { officialReferenceUrl });

    await saveButton.trigger('click');
    await flushPromises();

    expect(ElMessage.error).toHaveBeenCalledWith(
      '官方参考地址必须与存储类型匹配，使用 NetApp 或 Dell 官方 HTTPS 地址，且不能包含空格、认证信息、端口或 @ 字符',
    );
    expect(vendorEventDefinitionApi.create).not.toHaveBeenCalled();
  });

  it.each([
    'https://www.dell.com/support/manuals/en-us/powerscale-onefs/events',
    'https://infohub.delltechnologies.com/en-us/l/powerscale-onefs/events/',
  ])('accepts a Dell official subdomain for a pending definition: %s', async (officialReferenceUrl) => {
    const wrapper = await mountPage();
    const saveButton = await fillDefinitionForm(wrapper, {
      storageType: 'isilon',
      officialReferenceUrl,
    });

    await saveButton.trigger('click');
    await flushPromises();

    expect(vendorEventDefinitionApi.create).toHaveBeenCalledWith(expect.objectContaining({
      official_reference_url: officialReferenceUrl,
      review_status: 'pending',
    }));
  });

  it('allows a reviewed definition when classification and official evidence are complete', async () => {
    const wrapper = await mountPage();
    const saveButton = await fillDefinitionForm(wrapper, {
      associationType: 'fault_log',
      reviewStatus: 'reviewed',
      officialReferenceUrl: 'https://docs.netapp.com/us-en/ontap-ems-9181/',
      versionScope: 'ONTAP 9.18.1',
    });

    await saveButton.trigger('click');
    await flushPromises();

    expect(vendorEventDefinitionApi.create).toHaveBeenCalledWith(expect.objectContaining({
      association_type: 'fault_log',
      official_reference_url: 'https://docs.netapp.com/us-en/ontap-ems-9181/',
      version_scope: 'ONTAP 9.18.1',
      review_status: 'reviewed',
    }));
  });

  it('applies the reviewed evidence boundary when editing an existing definition', async () => {
    const wrapper = await mountPage();

    await wrapper.get('[data-testid="event-association-edit-1"]').trigger('click');
    const dialog = wrapper.findComponent({ name: 'ElDialog' });
    await dialog.findAllComponents({ name: 'ElInput' })[4]
      .vm.$emit('update:modelValue', '');
    await dialog.findAllComponents({ name: 'ElButton' })
      .find((button) => button.text() === '保存')
      .trigger('click');
    await flushPromises();

    expect(ElMessage.error).toHaveBeenCalledWith('已审核定义必须填写适用版本');
    expect(vendorEventDefinitionApi.update).not.toHaveBeenCalled();
  });
});
