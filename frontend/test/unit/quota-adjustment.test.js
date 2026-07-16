import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const apis = vi.hoisted(() => ({
  group: { adjustQuota: vi.fn(() => Promise.resolve({ id: 1 })) },
  usage: { adjustQuota: vi.fn(() => Promise.resolve({ id: 2 })) },
  confirm: vi.fn(() => Promise.resolve()),
  success: vi.fn(),
}));

vi.mock('@/api/group-api.js', () => ({ default: apis.group }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: apis.usage }));
vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessageBox: { confirm: apis.confirm },
  ElMessage: { success: apis.success },
}));

const passthrough = (name) => defineComponent({
  name,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const stubs = {
  ElDialog: defineComponent({
    name: 'ElDialog',
    setup(_, { attrs, slots }) {
      return () => h('div', attrs, [slots.default?.(), slots.footer?.()]);
    },
  }),
  ElForm: defineComponent({
    name: 'ElForm',
    props: { labelPosition: String },
    setup(_, { attrs, slots, expose }) {
      expose({ validate: () => Promise.resolve() });
      return () => h('form', attrs, slots.default?.());
    },
  }),
  ElFormItem: defineComponent({
    name: 'ElFormItem',
    props: { label: String },
    setup(props, { slots }) {
      return () => h('label', [props.label, slots.default?.()]);
    },
  }),
  ElInputNumber: defineComponent({ name: 'ElInputNumber', template: '<input />' }),
  ElSelect: defineComponent({
    name: 'ElSelect',
    props: { modelValue: String, disabled: Boolean },
    setup(props, { slots }) {
      return () => h('select', { disabled: props.disabled }, slots.default?.());
    },
  }),
  ElOption: passthrough('ElOption'),
  ElButton: defineComponent({
    name: 'ElButton',
    emits: ['click'],
    setup(_, { emit, slots }) {
      return () => h('button', { onClick: () => emit('click') }, slots.default?.());
    },
  }),
};

const row = (overrides = {}) => ({
  id: 1,
  name: 'project-a',
  limit: 100,
  soft_limit: 80,
  used: 60,
  storage_cluster: { storage_type: 'netapp' },
  storage_target: { type: 'qtree', name: 'qtree-a' },
  ...overrides,
});

async function mountDialog(resourceType = 'group') {
  const { default: QuotaAdjustmentDialog } = await import('@/components/form/QuotaAdjustmentDialog.vue');
  return shallowMount(QuotaAdjustmentDialog, {
    props: { resourceType },
    global: { stubs },
  });
}

describe('quota adjustment dialog', () => {
  beforeEach(() => vi.clearAllMocks());

  it('hides the soft limit for NetApp volume groups', async () => {
    const wrapper = await mountDialog();
    wrapper.vm.$.exposed.open(row({ storage_target: { type: 'volume', name: 'vol-a' } }));
    await flushPromises();

    expect(wrapper.text()).toContain('硬限额');
    expect(wrapper.text()).not.toContain('软限额');
  });

  it('shows soft grace only for Isilon and submits the final user quota', async () => {
    const wrapper = await mountDialog('storage_usage');
    wrapper.vm.$.exposed.open(row({
      id: 9,
      user: { rd_username: 'alice' },
      storage_cluster: { storage_type: 'isilon' },
      storage_target: { type: 'volume', name: 'dir-a' },
    }));
    await flushPromises();

    expect(wrapper.text()).toContain('软限额宽限期');
    wrapper.vm.$.exposed.model.hard_limit = 120;
    wrapper.vm.$.exposed.model.soft_limit = 90;
    wrapper.vm.$.exposed.model.soft_grace = 7;
    wrapper.vm.$.exposed.model.soft_grace_unit = 'days';
    await wrapper.findAll('button').find((button) => button.text() === '确认调整').trigger('click');
    await flushPromises();

    expect(apis.usage.adjustQuota).toHaveBeenCalledWith(9, {
      hard_limit: 120,
      soft_limit: 90,
      unit: 'GiB',
      soft_grace: 7,
      soft_grace_unit: 'days',
    });
    expect(wrapper.emitted('submitted')).toBeTruthy();
  });

  it('uses the global write form layout and keeps the soft-limit unit selectable', async () => {
    const wrapper = await mountDialog('storage_usage');
    wrapper.vm.$.exposed.open(row({
      storage_cluster: { storage_type: 'isilon' },
    }));
    await flushPromises();

    expect(wrapper.findComponent({ name: 'ElDialog' }).classes()).toEqual(
      expect.arrayContaining(['write-form-dialog', 'write-form-dialog--compact']),
    );
    expect(wrapper.findComponent({ name: 'ElForm' }).classes()).toContain('write-form');
    expect(wrapper.findComponent({ name: 'ElForm' }).props('labelPosition')).toBe('top');
    const unitSelects = wrapper.findAllComponents({ name: 'ElSelect' });
    expect(unitSelects).toHaveLength(3);
    expect(unitSelects.at(0).props('modelValue')).toBe('GiB');
    expect(unitSelects.at(1).props('modelValue')).toBe('GiB');
    expect(unitSelects.at(1).props('disabled')).toBe(false);

    wrapper.vm.$.exposed.model.hard_limit = 1024;
    wrapper.vm.$.exposed.model.soft_limit = 512;
    unitSelects.at(1).vm.$emit('update:modelValue', 'TiB');
    await flushPromises();
    expect(wrapper.vm.$.exposed.model).toMatchObject({
      hard_limit: 1,
      soft_limit: 0.5,
      unit: 'TiB',
    });
  });

  it('asks for confirmation before shrinking below the current hard limit', async () => {
    const wrapper = await mountDialog();
    wrapper.vm.$.exposed.open(row());
    wrapper.vm.$.exposed.model.hard_limit = 50;
    wrapper.vm.$.exposed.model.soft_limit = null;
    await wrapper.findAll('button').find((button) => button.text() === '确认调整').trigger('click');
    await flushPromises();

    expect(apis.confirm).toHaveBeenCalled();
    expect(apis.group.adjustQuota).toHaveBeenCalledWith(1, expect.objectContaining({ hard_limit: 50 }));
  });
});
