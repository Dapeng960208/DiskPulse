import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

const apis = vi.hoisted(() => ({
  group: {
    adjustQuota: vi.fn(() => Promise.resolve({ id: 1 })),
    quotaHistory: vi.fn(() => Promise.resolve([])),
    reconcileQuota: vi.fn(() => Promise.resolve()),
  },
  usage: {
    adjustQuota: vi.fn(() => Promise.resolve({ id: 2 })),
    quotaHistory: vi.fn(() => Promise.resolve([])),
    reconcileQuota: vi.fn(() => Promise.resolve()),
  },
  confirm: vi.fn(() => Promise.resolve()),
  success: vi.fn(),
  warning: vi.fn(),
}));

vi.mock('@/api/group-api.js', () => ({ default: apis.group }));
vi.mock('@/api/storage-usage-api.js', () => ({ default: apis.usage }));
vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessageBox: { confirm: apis.confirm },
  ElMessage: { success: apis.success, warning: apis.warning },
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
  ElInputNumber: defineComponent({
    name: 'ElInputNumber',
    props: { modelValue: Number },
    emits: ['update:modelValue'],
    template: '<input />',
  }),
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
    emits: ['click', 'update:modelValue'],
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

  it('defaults missing soft limit and Isilon grace before submitting a user quota', async () => {
    const wrapper = await mountDialog('storage_usage');
    wrapper.vm.$.exposed.open(row({
      id: 9,
      limit: 120,
      soft_limit: null,
      user: { rd_username: 'alice' },
      storage_cluster: { storage_type: 'isilon' },
      storage_target: { type: 'volume', name: 'dir-a' },
    }));
    await flushPromises();

    expect(wrapper.text()).toContain('软限额宽限期');
    expect(wrapper.vm.$.exposed.model).toMatchObject({
      hard_limit: 120,
      soft_limit: 108,
      soft_grace: 7,
      soft_grace_unit: 'days',
    });
    await wrapper.findAll('button').find((button) => button.text() === '确认调整').trigger('click');
    await flushPromises();

    expect(apis.usage.adjustQuota).toHaveBeenCalledWith(9, {
      hard_limit: 120,
      soft_limit: 108,
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

  it('reconciles an unknown device outcome and refreshes quota history', async () => {
    const unknownOutcome = Object.assign(new Error('unknown'), {
      response: { data: { detail: { code: 'quota_outcome_unknown' } } },
    });
    apis.group.adjustQuota.mockRejectedValueOnce(unknownOutcome);
    apis.group.quotaHistory
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: 1, action: 'reconcile', outcome: 'success', occurred_at: 'now' }]);
    const wrapper = await mountDialog();
    wrapper.vm.$.exposed.open(row());
    await flushPromises();

    await expect(wrapper.vm.$.setupState.submit()).rejects.toBe(unknownOutcome);
    expect(apis.warning).toHaveBeenCalledWith('设备写入结果未知，请执行只读对账');

    await wrapper.findAll('button').find((button) => button.text() === '只读对账').trigger('click');
    await flushPromises();

    expect(apis.group.reconcileQuota).toHaveBeenCalledWith(1);
    expect(apis.group.quotaHistory).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('reconcile · success · now');
  });

  it('updates quota fields through their v-model bindings', async () => {
    const wrapper = await mountDialog('storage_usage');
    wrapper.vm.$.exposed.open(row({
      storage_cluster: { storage_type: 'isilon' },
    }));
    await flushPromises();

    const numberInputs = wrapper.findAllComponents({ name: 'ElInputNumber' });
    await numberInputs[0].vm.$emit('update:modelValue', 90);
    await numberInputs[1].vm.$emit('update:modelValue', 70);
    await numberInputs[2].vm.$emit('update:modelValue', 5);
    const selects = wrapper.findAllComponents({ name: 'ElSelect' });
    await selects[2].vm.$emit('update:modelValue', 'hours');

    expect(wrapper.vm.$.exposed.model).toMatchObject({
      hard_limit: 90,
      soft_limit: 70,
      soft_grace: 5,
      soft_grace_unit: 'hours',
    });
  });
});
