/* eslint-disable vue/one-component-per-file -- this file intentionally groups Element Plus test stubs. */
import { defineComponent, h, nextTick } from 'vue';
import { flushPromises, mount } from '@vue/test-utils';
import { vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  host: { fetch: vi.fn(), fetchById: vi.fn() },
  users: { fetch: vi.fn(), fetchById: vi.fn() },
  groupTag: { fetch: vi.fn(), fetchById: vi.fn() },
  qtree: { fetch: vi.fn(), fetchById: vi.fn() },
  volume: { fetch: vi.fn(), fetchById: vi.fn() },
  aggregate: { fetch: vi.fn(), fetchById: vi.fn() },
  domainGroup: { fetch: vi.fn() },
  storageCluster: { fetch: vi.fn(), fetchById: vi.fn() },
  storageUsage: { fetch: vi.fn(), fetchById: vi.fn() },
}));

vi.mock('@/api/host-api.js', () => ({ default: mocks.host }));
vi.mock('@/api/users-api.js', () => ({ default: mocks.users }));
vi.mock('@/api/group-tag-api', () => ({ default: mocks.groupTag }));
vi.mock('@/api/qtree-api', () => ({ default: mocks.qtree }));
vi.mock('@/api/volume-api', () => ({ default: mocks.volume }));
vi.mock('@/api/aggregate-api', () => ({ default: mocks.aggregate }));
vi.mock('@/api/domain-group-api', () => ({ default: mocks.domainGroup }));
vi.mock('@/api/storage-cluster-api', () => ({ default: mocks.storageCluster }));
vi.mock('@/api/storage-usage-api', () => ({ default: mocks.storageUsage }));
vi.mock('@/components/data/UserAvatar.vue', () => ({
  default: defineComponent({
    name: 'UserAvatar',
    setup: () => () => h('span'),
  }),
}));

const ElSelect = defineComponent({
  name: 'ElSelect',
  props: {
    modelValue: { type: [String, Number, Array], default: null },
    remoteMethod: { type: Function, default: null },
    loading: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'change'],
  setup(props, { emit, slots }) {
    return () => h('div', { 'data-test': 'el-select' }, [
      h('input', {
        'data-test': 'select-input',
        disabled: props.disabled,
        onInput: (event) => props.remoteMethod?.(event.target.value),
      }),
      slots.default?.(),
      h('button', {
        type: 'button',
        'data-test': 'select-update',
        onClick: () => emit('update:modelValue', props.modelValue),
      }),
    ]);
  },
});

const ElOption = defineComponent({
  name: 'ElOption',
  props: {
    label: { type: String, default: '' },
    value: { type: [String, Number], default: null },
    disabled: { type: Boolean, default: false },
  },
  setup(props, { slots }) {
    return () => h('option', {
      value: props.value,
      disabled: props.disabled,
    }, slots.default?.() ?? props.label);
  },
});

const elementStubs = {
  ElSelect,
  ElOption,
  ElSpace: defineComponent({ name: 'ElSpace', setup: (_, { slots }) => () => h('div', slots.default?.()) }),
  ElFormItem: defineComponent({ name: 'ElFormItem', setup: (_, { slots }) => () => h('div', slots.default?.()) }),
  ElInputNumber: defineComponent({
    name: 'ElInputNumber',
    props: {
      modelValue: { type: Number, default: null },
      disabled: { type: Boolean, default: false },
      min: { type: Number, default: undefined },
      max: { type: Number, default: undefined },
      step: { type: Number, default: undefined },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
      return () => h('input', {
        type: 'number',
        value: props.modelValue,
        disabled: props.disabled,
        onInput: (event) => emit('update:modelValue', Number(event.target.value)),
      });
    },
  }),
  ElAlert: defineComponent({
    name: 'ElAlert',
    props: { title: { type: String, default: '' } },
    setup: (props) => () => h('div', { 'data-test': 'alert' }, props.title),
  }),
  ElProgress: defineComponent({
    name: 'ElProgress',
    props: {
      percentage: { type: Number, default: 0 },
      color: { type: [String, Function], default: '' },
      style: { type: [String, Object], default: undefined },
    },
    setup: () => () => h('div'),
  }),
  ElTransfer: defineComponent({
    name: 'ElTransfer',
    props: {
      modelValue: { type: Array, default: () => [] },
      data: { type: Array, default: () => [] },
    },
    emits: ['update:modelValue'],
    setup: () => () => h('div'),
  }),
  ElTag: defineComponent({ name: 'ElTag', setup: (_, { slots }) => () => h('span', slots.default?.()) }),
};

function resetMock(fn, implementation) {
  fn.mockReset();
  fn.mockImplementation(implementation);
}

function resetApiMocks() {
  resetMock(mocks.host.fetch, () => Promise.resolve({ content: [{ id: 1, name: 'Host 1' }] }));
  resetMock(mocks.host.fetchById, (id) => Promise.resolve({ id, name: `Host ${id}` }));
  resetMock(mocks.users.fetch, () => Promise.resolve({
    content: [
      { id: 1, rd_username: 'alice', username: 'alice', department: 'RD', avatar_url: null },
      { id: 2, rd_username: 'bob', username: null, department: '', avatar_url: null },
    ],
  }));
  resetMock(mocks.users.fetchById, (id) => Promise.resolve({
    id,
    rd_username: `user-${id}`,
    username: null,
    department: '',
    avatar_url: null,
  }));
  resetMock(mocks.groupTag.fetch, () => Promise.resolve({ content: [{ id: 1, name: 'Tag 1' }] }));
  resetMock(mocks.groupTag.fetchById, (id) => Promise.resolve({ id, name: `Tag ${id}` }));
  resetMock(mocks.qtree.fetch, () => Promise.resolve({
    content: [{ id: 1, name: 'Qtree 1', volume: { name: 'Volume 1' } }],
  }));
  resetMock(mocks.qtree.fetchById, (id) => Promise.resolve({ id, name: `Qtree ${id}` }));
  resetMock(mocks.volume.fetch, () => Promise.resolve({ content: [{ id: 1, name: 'Volume 1' }] }));
  resetMock(mocks.volume.fetchById, (id) => Promise.resolve({ id, name: `Volume ${id}` }));
  resetMock(mocks.aggregate.fetch, () => Promise.resolve({ content: [{ id: 1, name: 'Aggregate 1' }] }));
  resetMock(mocks.aggregate.fetchById, (id) => Promise.resolve({ id, name: `Aggregate ${id}` }));
  resetMock(mocks.domainGroup.fetch, () => Promise.resolve({
    result: { content: [{ id: 1, name: 'Group 1', emailAddress: 'group@example.com' }] },
  }));
  resetMock(mocks.storageCluster.fetch, () => Promise.resolve({ content: [{ id: 1, name: 'Cluster 1' }] }));
  resetMock(mocks.storageCluster.fetchById, (id) => Promise.resolve({ id, name: `Cluster ${id}` }));
  resetMock(mocks.storageUsage.fetch, () => Promise.resolve({ content: [{ id: 1, linux_path: '/home/alice' }] }));
  resetMock(mocks.storageUsage.fetchById, (id) => Promise.resolve({ id, linux_path: `/home/user-${id}` }));
}

function mountComponent(component, props = {}) {
  return mount(component, { props, global: { stubs: elementStubs } });
}

async function settle() {
  await flushPromises();
  await nextTick();
}

function validRule() {
  return {
    quota_basis: 'hard',
    important: { threshold: 80, repeat_hours: 24 },
    serious: { threshold: 90, repeat_hours: 6 },
    emergency: { threshold: 95, repeat_hours: 1 },
  };
}

beforeEach(() => {
  resetApiMocks();
});

describe('select component coverage gaps', () => {
  it('covers HostsSelect defaults, input search, update transform, and init options', async () => {
    const { default: HostsSelect } = await import('@/components/form/HostsSelect.vue');
    const wrapper = mountComponent(HostsSelect, { modelValue: null, returnField: 'name' });
    await settle();

    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.host.fetch).toHaveBeenCalledWith({ page: 1, size: 20 });
    await select.find('input').setValue('edge');
    await settle();
    expect(mocks.host.fetch).toHaveBeenLastCalledWith({ nameLike: 'edge' });
    expect(select.props('loading')).toBe(false);
    const calls = mocks.host.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.host.fetch).toHaveBeenCalledTimes(calls);
    await select.vm.$emit('update:modelValue', 1);
    expect(wrapper.emitted('update:modelValue')).toContainEqual(['Host 1']);
    wrapper.unmount();

    const withInitOption = mountComponent(HostsSelect, {
      modelValue: [1],
      multiple: true,
      initOption: [{ id: 1, name: 'Initial host' }],
      returnField: 'name',
    });
    await settle();
    const multiSelect = withInitOption.findComponent({ name: 'ElSelect' });
    await multiSelect.vm.$emit('update:modelValue', [1]);
    expect(withInitOption.emitted('update:modelValue')).toContainEqual([['Initial host']]);
    expect(mocks.host.fetchById).not.toHaveBeenCalled();
    withInitOption.unmount();
  });

  it('covers HostsSelect selected-id loading and multiple fetchById paths', async () => {
    const { default: HostsSelect } = await import('@/components/form/HostsSelect.vue');
    const wrapper = mountComponent(HostsSelect, { modelValue: 8 });
    await settle();
    expect(mocks.host.fetchById).toHaveBeenCalledWith(8);
    wrapper.unmount();

    const multiple = mountComponent(HostsSelect, { modelValue: [8, 9], multiple: true });
    await settle();
    expect(mocks.host.fetchById).toHaveBeenCalledWith(8);
    expect(mocks.host.fetchById).toHaveBeenCalledWith(9);
    multiple.unmount();
  });

  it('covers RdUserSelect defaults, search, returnField, and init options', async () => {
    const { default: RdUserSelect } = await import('@/components/form/RdUserSelect.vue');
    const wrapper = mountComponent(RdUserSelect, { modelValue: null, returnField: 'rd_username' });
    await settle();

    const select = wrapper.findComponent({ name: 'ElSelect' });
    await select.find('input').setValue('ali');
    await settle();
    expect(mocks.users.fetch).toHaveBeenLastCalledWith({ nameLike: 'ali' });
    await select.vm.$emit('update:modelValue', 1);
    expect(wrapper.emitted('update:modelValue')).toContainEqual(['alice']);
    const calls = mocks.users.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.users.fetch).toHaveBeenCalledTimes(calls);
    wrapper.unmount();

    const withInitOption = mountComponent(RdUserSelect, {
      modelValue: [1],
      multiple: true,
      initOption: [{ id: 1, rd_username: 'Initial user' }],
      returnField: 'rd_username',
    });
    await settle();
    await withInitOption.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', [1]);
    expect(withInitOption.emitted('update:modelValue')).toContainEqual([['Initial user']]);
    withInitOption.unmount();
  });

  it('covers RdUserSelect selected-id and multiple API initialization', async () => {
    const { default: RdUserSelect } = await import('@/components/form/RdUserSelect.vue');
    const wrapper = mountComponent(RdUserSelect, { modelValue: 3 });
    await settle();
    expect(mocks.users.fetchById).toHaveBeenCalledWith(3);
    wrapper.unmount();

    const multiple = mountComponent(RdUserSelect, { modelValue: [3, 4], multiple: true });
    await settle();
    expect(mocks.users.fetchById).toHaveBeenCalledWith(3);
    expect(mocks.users.fetchById).toHaveBeenCalledWith(4);
    multiple.unmount();
  });

  it('covers GroupTagSelect loading, labels, empty search, and API error cleanup', async () => {
    const { default: GroupTagSelect } = await import('@/components/form/GroupTagSelect.vue');
    const wrapper = mountComponent(GroupTagSelect, { modelValue: null });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.groupTag.fetch).toHaveBeenCalledWith({ page: 1, size: 20 });

    await select.find('input').setValue('ops');
    await settle();
    expect(mocks.groupTag.fetch).toHaveBeenLastCalledWith({ nameLike: 'ops', page: 1, size: 20 });
    await select.vm.$emit('change', 1);
    expect(wrapper.emitted('selected-label-change')).toContainEqual(['Tag 1']);

    await select.props('remoteMethod')('');
    await settle();
    expect(mocks.groupTag.fetch).toHaveBeenLastCalledWith({ nameLike: null, page: 1, size: 20 });
    mocks.groupTag.fetch.mockRejectedValueOnce(new Error('network'));
    await expect(select.props('remoteMethod')('broken')).rejects.toThrow('network');
    expect(select.props('loading')).toBe(false);
    wrapper.unmount();
  });

  it('covers StorageAlertRuleForm updates, disabled controls, and validation branches', async () => {
    const { default: StorageAlertRuleForm } = await import('@/components/form/StorageAlertRuleForm.vue');
    const rule = validRule();
    const wrapper = mountComponent(StorageAlertRuleForm, { modelValue: rule });
    expect(wrapper.emitted('validity-change')).toContainEqual([true]);

    await wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('update:modelValue', 'soft');
    expect(wrapper.emitted('update:modelValue')).toContainEqual([{
      ...rule,
      quota_basis: 'soft',
    }]);
    await wrapper.findAllComponents({ name: 'ElInputNumber' })[0].vm.$emit('update:modelValue', 70);
    expect(wrapper.emitted('update:modelValue')).toContainEqual([{
      ...rule,
      important: { ...rule.important, threshold: 70 },
    }]);

    await wrapper.setProps({ disabled: true });
    expect(wrapper.findComponent({ name: 'ElSelect' }).props('disabled')).toBe(true);
    expect(wrapper.findAllComponents({ name: 'ElInputNumber' })[0].props('disabled')).toBe(true);

    await wrapper.setProps({ modelValue: { ...rule, quota_basis: 'other' } });
    expect(wrapper.findComponent({ name: 'ElAlert' }).props('title')).toBe('请选择有效的限额口径');
    await wrapper.setProps({ modelValue: { ...rule, important: { threshold: 0, repeat_hours: 24 } } });
    expect(wrapper.findComponent({ name: 'ElAlert' }).props('title')).toBe('阈值必须是 1 到 100 的整数');
    await wrapper.setProps({ modelValue: {
      ...rule,
      important: { threshold: 90, repeat_hours: 24 },
    } });
    expect(wrapper.findComponent({ name: 'ElAlert' }).props('title')).toBe('重要阈值必须小于严重阈值');
    await wrapper.setProps({ modelValue: {
      ...rule,
      serious: { threshold: 95, repeat_hours: 6 },
    } });
    expect(wrapper.findComponent({ name: 'ElAlert' }).props('title')).toBe('严重阈值必须小于紧急阈值');
    await wrapper.setProps({ modelValue: {
      ...rule,
      important: { threshold: 80, repeat_hours: 0 },
    } });
    expect(wrapper.findComponent({ name: 'ElAlert' }).props('title')).toBe('重复通知频次必须是正整数');
    await wrapper.setProps({ modelValue: rule });
    expect(wrapper.findComponent({ name: 'ElAlert' }).exists()).toBe(false);
    wrapper.unmount();
  });

  it('covers Progress percentage guards, clamping, display, and color thresholds', async () => {
    const { default: Progress } = await import('@/components/form/Progress.vue');
    const wrapper = mountComponent(Progress, { used: 50, total: 100 });
    const progress = wrapper.findComponent({ name: 'ElProgress' });
    expect(progress.props('percentage')).toBe(50);
    expect(progress.props('color')(79)).toBe('#34D399');
    expect(progress.props('color')(80)).toBe('#F59E0B');
    expect(progress.props('color')(90)).toBe('#EF4444');
    expect(wrapper.find('.progress-numbers').exists()).toBe(true);
    wrapper.unmount();

    const zero = mountComponent(Progress, { used: 0, total: 0, showNumbers: false });
    expect(zero.findComponent({ name: 'ElProgress' }).props('percentage')).toBe(0);
    expect(zero.findComponent({ name: 'ElProgress' }).props('style')).toEqual({ width: '100%' });
    expect(zero.find('.progress-numbers').exists()).toBe(false);
    zero.unmount();

    const nullValue = mountComponent(Progress, { used: null, total: null });
    expect(nullValue.findComponent({ name: 'ElProgress' }).props('percentage')).toBe(0);
    nullValue.unmount();

    const high = mountComponent(Progress, { used: 150, total: 100 });
    expect(high.findComponent({ name: 'ElProgress' }).props('percentage')).toBe(100);
    high.unmount();

    const negative = mountComponent(Progress, { used: -1, total: 100 });
    expect(negative.findComponent({ name: 'ElProgress' }).exists()).toBe(false);
    negative.unmount();
  });

  it('covers QtreeSelect scoped query, search, labels, and watcher refresh', async () => {
    mocks.qtree.fetch.mockResolvedValueOnce({ content: [
      { id: 5, name: 'Qtree 5', volume: { name: 'Volume A' } },
      { id: 6, name: 'Qtree 6' },
    ] });
    const { default: QtreeSelect } = await import('@/components/form/QtreeSelect.vue');
    const wrapper = mountComponent(QtreeSelect, {
      modelValue: null,
      multiple: true,
      volumeId: 2,
      storageClusterId: 3,
    });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.qtree.fetch).toHaveBeenCalledWith({
      page: 1,
      size: 20,
      volume_id: 2,
      storage_cluster_id: 3,
    });
    mocks.qtree.fetch.mockResolvedValueOnce({ content: [
      { id: 5, name: 'Qtree 5', volume: { name: 'Volume A' } },
      { id: 6, name: 'Qtree 6' },
    ] });
    await select.find('input').setValue('logs');
    await settle();
    expect(mocks.qtree.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      volume_id: 2,
      storage_cluster_id: 3,
      nameLike: 'logs',
    });
    const calls = mocks.qtree.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.qtree.fetch).toHaveBeenCalledTimes(calls);
    await select.vm.$emit('change', [5, 6]);
    expect(wrapper.emitted('selected-label-change')).toContainEqual(['Volume A/Qtree 5、Qtree 6']);
    await select.vm.$emit('change', []);
    expect(wrapper.emitted('selected-label-change')).toContainEqual([null]);
    await wrapper.setProps({ volumeId: 4 });
    await settle();
    expect(mocks.qtree.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      volume_id: 4,
      storage_cluster_id: 3,
    });
    wrapper.unmount();
  });

  it('covers QtreeSelect selected-value initialization', async () => {
    const { default: QtreeSelect } = await import('@/components/form/QtreeSelect.vue');
    const wrapper = mountComponent(QtreeSelect, { modelValue: 7 });
    await settle();
    expect(mocks.qtree.fetchById).toHaveBeenCalledWith(7);
    wrapper.unmount();
  });

  it('covers VolumeSelect scoped query, search, labels, and model updates', async () => {
    mocks.volume.fetch.mockResolvedValueOnce({ content: [{ id: 11, name: 'Volume 11' }] });
    const { default: VolumeSelect } = await import('@/components/form/VolumeSelect.vue');
    const wrapper = mountComponent(VolumeSelect, { modelValue: null, storageClusterId: 4 });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.volume.fetch).toHaveBeenCalledWith({ page: 1, size: 20, storage_cluster_id: 4 });
    mocks.volume.fetch.mockResolvedValueOnce({ content: [{ id: 11, name: 'Volume 11' }] });
    await select.find('input').setValue('data');
    await settle();
    expect(mocks.volume.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      storage_cluster_id: 4,
      nameLike: 'data',
    });
    await select.vm.$emit('change', 11);
    expect(wrapper.emitted('selected-label-change')).toContainEqual(['Volume 11']);
    await select.vm.$emit('update:modelValue', 11);
    expect(wrapper.emitted('update:modelValue')).toContainEqual([11]);
    await wrapper.setProps({ storageClusterId: 5 });
    await settle();
    expect(mocks.volume.fetch).toHaveBeenLastCalledWith({ page: 1, size: 20, storage_cluster_id: 5 });
    wrapper.unmount();
  });

  it('covers VolumeSelect selected-value initialization', async () => {
    const { default: VolumeSelect } = await import('@/components/form/VolumeSelect.vue');
    const wrapper = mountComponent(VolumeSelect, { modelValue: [7], multiple: true });
    await settle();
    expect(mocks.volume.fetchById).toHaveBeenCalledWith(7);
    wrapper.unmount();
  });

  it('covers AggregateSelect defaults, selected ids, search, and model updates', async () => {
    const { default: AggregateSelect } = await import('@/components/form/AggregateSelect.vue');
    const wrapper = mountComponent(AggregateSelect, { modelValue: null });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.aggregate.fetch).toHaveBeenCalledWith({ page: 1, size: 20 });
    await select.find('input').setValue('fast');
    await settle();
    expect(mocks.aggregate.fetch).toHaveBeenLastCalledWith({ nameLike: 'fast' });
    const calls = mocks.aggregate.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.aggregate.fetch).toHaveBeenCalledTimes(calls);
    await select.vm.$emit('update:modelValue', 1);
    expect(wrapper.emitted('update:modelValue')).toContainEqual([1]);
    wrapper.unmount();

    const selected = mountComponent(AggregateSelect, { modelValue: [2, 3], multiple: true });
    await settle();
    expect(mocks.aggregate.fetchById).toHaveBeenCalledWith(2);
    expect(mocks.aggregate.fetchById).toHaveBeenCalledWith(3);
    selected.unmount();
  });

  it('covers StorageClusterSelect defaults, selected ids, search, and empty query', async () => {
    const { default: StorageClusterSelect } = await import('@/components/form/StorageClusterSelect.vue');
    const wrapper = mountComponent(StorageClusterSelect, { modelValue: null });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.storageCluster.fetch).toHaveBeenCalledWith({ page: 1, size: 20 });
    await select.find('input').setValue('prod');
    await settle();
    expect(mocks.storageCluster.fetch).toHaveBeenLastCalledWith({ nameLike: 'prod' });
    const calls = mocks.storageCluster.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.storageCluster.fetch).toHaveBeenCalledTimes(calls);
    wrapper.unmount();

    const selected = mountComponent(StorageClusterSelect, { modelValue: [2], multiple: true });
    await settle();
    expect(mocks.storageCluster.fetchById).toHaveBeenCalledWith(2);
    selected.unmount();
  });

  it('covers StorageUsageSelect volume-scoped query, search, empty query, and selected id', async () => {
    const { default: StorageUsageSelect } = await import('@/components/form/StorageUsageSelect.vue');
    const wrapper = mountComponent(StorageUsageSelect, { modelValue: null, volumeId: 9 });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(mocks.storageUsage.fetch).toHaveBeenCalledWith({ page: 1, size: 20, volume_id: 9 });
    await select.find('input').setValue('alice');
    await settle();
    expect(mocks.storageUsage.fetch).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      volume_id: 9,
      nameLike: 'alice',
    });
    const calls = mocks.storageUsage.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.storageUsage.fetch).toHaveBeenCalledTimes(calls);
    wrapper.unmount();

    const selected = mountComponent(StorageUsageSelect, { modelValue: 3, volumeId: 9 });
    await settle();
    expect(mocks.storageUsage.fetchById).toHaveBeenCalledWith(3);
    selected.unmount();
  });

  it('covers DomainGroupSelect defaults, disabled option, type search, and model reset', async () => {
    const { default: DomainGroupSelect } = await import('@/components/form/DomainGroupSelect.vue');
    const options = [
      { id: 1, name: 'Distribution', emailAddress: 'distribution@example.com' },
      { id: 2, name: 'Security', emailAddress: 'security@example.com' },
    ];
    const wrapper = mountComponent(DomainGroupSelect, {
      modelValue: null,
      type: 'distribution',
      defaultOptions: options,
      disabledGroupId: 1,
    });
    await settle();
    const select = wrapper.findComponent({ name: 'ElSelect' });
    expect(wrapper.findAllComponents({ name: 'ElOption' })[0].props('disabled')).toBe(true);
    await select.find('input').setValue('dist');
    await settle();
    expect(mocks.domainGroup.fetch).toHaveBeenLastCalledWith({
      nameLike: 'dist',
      isEmailEnabled: true,
    });
    const calls = mocks.domainGroup.fetch.mock.calls.length;
    await select.props('remoteMethod')('');
    expect(mocks.domainGroup.fetch).toHaveBeenCalledTimes(calls);
    await wrapper.setProps({ type: 'security', defaultOptions: options });
    await select.props('remoteMethod')('sec');
    await settle();
    expect(mocks.domainGroup.fetch).toHaveBeenLastCalledWith({
      nameLike: 'sec',
      isEmailEnabled: false,
    });
    await wrapper.setProps({ multiple: true });
    await wrapper.setProps({ multiple: false });
    expect(wrapper.emitted('update:modelValue')).toContainEqual([[]]);
    expect(wrapper.emitted('update:modelValue')).toContainEqual([null]);
    wrapper.unmount();
  });

  it('covers RdUserTransfer loading, return fields, fallback ids, and prop sync branch', async () => {
    const { default: RdUserTransfer } = await import('@/components/form/RdUserTransfer.vue');
    const wrapper = mountComponent(RdUserTransfer, { modelValue: [], returnField: 'rd_username' });
    expect(wrapper.findComponent({ name: 'ElTransfer' }).exists()).toBe(false);
    await settle();
    const transfer = wrapper.findComponent({ name: 'ElTransfer' });
    expect(mocks.users.fetch).toHaveBeenCalledWith({ page: 1, size: 10000, load_detail: false });
    expect(transfer.props('data')[0]).toMatchObject({ id: 1, disabled: false });
    await transfer.vm.$emit('update:modelValue', [1, 99]);
    await settle();
    expect(wrapper.emitted('update:modelValue')).toContainEqual([['alice', 99]]);
    await wrapper.setProps({ modelValue: [2] });
    await settle();
    expect(wrapper.emitted('update:modelValue')).toEqual([[['alice', 99]]]);
    expect(mocks.users.fetch).toHaveBeenCalledTimes(1);
    wrapper.unmount();
  });
});
