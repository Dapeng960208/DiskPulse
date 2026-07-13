import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineComponent, h, nextTick } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({
  default: {},
}));

vi.mock('@/api/support/auth-request', () => ({
  default: {},
}));

const ElButtonStub = defineComponent({
  name: 'ElButton',
  emits: ['click'],
  setup(_, { emit, slots }) {
    return () => h('button', { onClick: () => emit('click') }, slots.default?.());
  },
});

const ElDialogStub = defineComponent({
  name: 'ElDialog',
  setup(_, { slots }) {
    return () => h('div', [slots.default?.(), slots.footer?.()]);
  },
});

const ElFormStub = defineComponent({
  name: 'ElForm',
  props: {
    model: Object,
    rules: Object,
  },
  setup(_, { expose, slots }) {
    expose({
      validate: vi.fn(() => Promise.resolve()),
      clearValidate: vi.fn(),
    });
    return () => h('form', slots.default?.());
  },
});

const ElFormItemStub = defineComponent({
  name: 'ElFormItem',
  props: {
    label: String,
    prop: String,
  },
  setup(props, { slots }) {
    return () => h('label', [props.label, slots.default?.()]);
  },
});

const ElSelectStub = defineComponent({
  name: 'ElSelect',
  inheritAttrs: false,
  props: {
    modelValue: {
      type: [String, Number],
      default: null,
    },
  },
  emits: ['update:modelValue'],
  setup(props, { attrs, emit, slots }) {
    return () => h('select', {
      ...attrs,
      value: props.modelValue,
      onChange: (event) => emit('update:modelValue', event.target.value),
    }, slots.default?.());
  },
});

function createSelectStub(name) {
  return defineComponent({
    name,
    props: {
      modelValue: {
        type: [String, Number],
        default: null,
      },
      storageClusterId: {
        type: Number,
        default: null,
      },
    },
    emits: ['update:modelValue'],
    setup(_, { slots }) {
      return () => h('div', slots.default?.());
    },
  });
}

const ProjectSelectStub = createSelectStub('ProjectSelect');
const VolumeSelectStub = createSelectStub('VolumeSelect');
const QtreeSelectStub = createSelectStub('QtreeSelect');

const formStubs = {
  ElButton: ElButtonStub,
  ElDialog: ElDialogStub,
  ElForm: ElFormStub,
  ElFormItem: ElFormItemStub,
  ElInput: true,
  ElOption: true,
  ElSelect: ElSelectStub,
  ElSwitch: true,
  ElTag: true,
  ElTooltip: true,
  HostSelect: true,
  MailSelect: true,
  ProjectSelect: ProjectSelectStub,
  QtreeSelect: QtreeSelectStub,
  RdUserSelect: true,
  VolumeSelect: VolumeSelectStub,
};

function submitButton(wrapper) {
  return wrapper.findAll('button').find((button) => button.text() === '提交');
}

async function mountGroupForm(environmentResponse = { content: [], total: 0 }) {
  const { default: environmentApi } = await import('@/api/project-storage-environment-api');
  const fetchByProject = vi.spyOn(environmentApi, 'fetchByProject').mockResolvedValue(
    environmentResponse,
  );
  const { default: GroupFormDialog } = await import(
    '@/pages/group/components/GroupFormDialog.vue'
  );
  const wrapper = shallowMount(GroupFormDialog, {
    attachTo: document.body,
    global: { stubs: formStubs },
  });
  wrapper.vm.$.exposed.edit();
  await nextTick();
  return { fetchByProject, wrapper };
}

describe('group project storage environment binding', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it('passes project_environment_id through the group list API query', async () => {
    const { default: BaseApi } = await import('@/api/support/base-api');
    const get = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({
      content: [],
      total: 0,
    });
    const { default: groupApi } = await import('@/api/group-api');

    await groupApi.fetch({ project_environment_id: 11, page: 1, size: 20 });

    expect(groupApi.urlPrefix).toBe('/groups/');
    expect(get).toHaveBeenCalledWith('', {
      project_environment_id: 11,
      page: 1,
      size: 20,
    }, undefined);
  });

  it('renders unified environment and target summaries without traversing qtree.volume', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/group/GroupListPage.vue'),
      'utf8',
    );

    expect(source).toContain('project_environment');
    expect(source).toContain('storage_cluster?.storage_type');
    expect(source).toContain('storage_target?.type');
    expect(source).toContain('storage_target?.name');
    expect(source).not.toMatch(/(?:row|props\.row)\.qtree\??\.volume/);
  });

  it('sanitizes create and update payloads to one environment target', async () => {
    const { default: groupApi } = await import('@/api/group-api');
    const create = vi.spyOn(groupApi, 'create').mockResolvedValue({ id: 20 });
    const replace = vi.spyOn(groupApi, 'replace').mockResolvedValue({ id: 20 });
    const { wrapper } = await mountGroupForm();
    let form = wrapper.findComponent(ElFormStub);

    Object.assign(form.props('model'), {
      name: 'volume-group',
      project_id: 1,
      storage_cluster_id: 101,
      project_environment_id: 11,
      volume_id: 501,
      qtree_id: null,
    });
    await submitButton(wrapper).trigger('click');
    await flushPromises();

    const createPayload = create.mock.calls[0][0];
    expect(createPayload).toEqual(expect.objectContaining({
      project_environment_id: 11,
      volume_id: 501,
    }));
    expect(createPayload).not.toHaveProperty('qtree_id');
    expect(createPayload).not.toHaveProperty('project_id');
    expect(createPayload).not.toHaveProperty('storage_cluster_id');

    wrapper.vm.$.exposed.edit({
      id: 20,
      name: 'qtree-group',
      project_id: 1,
      storage_cluster_id: 101,
      project_environment_id: 11,
      volume_id: null,
      qtree_id: 601,
    });
    await nextTick();
    form = wrapper.findComponent(ElFormStub);
    await submitButton(wrapper).trigger('click');
    await flushPromises();

    const updatePayload = replace.mock.calls[0][1];
    expect(updatePayload).toEqual(expect.objectContaining({
      project_environment_id: 11,
      qtree_id: 601,
    }));
    expect(updatePayload).not.toHaveProperty('volume_id');
    expect(updatePayload).not.toHaveProperty('project_id');
    expect(updatePayload).not.toHaveProperty('storage_cluster_id');
  });

  it('cascades project to environment and clears lower selections', async () => {
    const environments = {
      content: [
        {
          id: 11,
          name: 'netapp-env',
          storage_cluster: { id: 101, name: 'netapp-1', storage_type: 'netapp' },
        },
        {
          id: 12,
          name: 'isilon-env',
          storage_cluster: { id: 102, name: 'isilon-1', storage_type: 'isilon' },
        },
      ],
      total: 2,
    };
    const { fetchByProject, wrapper } = await mountGroupForm(environments);
    const form = wrapper.findComponent(ElFormStub);
    Object.assign(form.props('model'), {
      project_environment_id: 99,
      volume_id: 501,
      qtree_id: 601,
    });

    wrapper.findComponent(ProjectSelectStub).vm.$emit('update:modelValue', 1);
    await flushPromises();

    expect(fetchByProject).toHaveBeenCalledWith(1, expect.objectContaining({
      page: 1,
    }));
    expect(form.props('model')).toEqual(expect.objectContaining({
      project_environment_id: null,
      volume_id: null,
      qtree_id: null,
    }));

    const environmentSelect = wrapper.findComponent(
      '[data-test="project-environment-select"]',
    );
    expect(environmentSelect.exists()).toBe(true);
    environmentSelect.vm.$emit('update:modelValue', 11);
    await nextTick();

    const targetTypeSelect = wrapper.findComponent('[data-test="storage-target-type"]');
    expect(targetTypeSelect.exists()).toBe(true);
    targetTypeSelect.vm.$emit('update:modelValue', 'qtree');
    await nextTick();
    expect(wrapper.findComponent(QtreeSelectStub).props('storageClusterId')).toBe(101);

    form.props('model').qtree_id = 601;
    targetTypeSelect.vm.$emit('update:modelValue', 'volume');
    await nextTick();
    expect(form.props('model').qtree_id).toBeNull();
    expect(form.props('model').volume_id).toBeNull();
    expect(wrapper.findComponent(VolumeSelectStub).props('storageClusterId')).toBe(101);
  });

  it('fixes Isilon to Volume while keeping the derived cluster read-only', async () => {
    const { wrapper } = await mountGroupForm({
      content: [
        {
          id: 12,
          name: 'isilon-env',
          storage_cluster: { id: 102, name: 'isilon-1', storage_type: 'isilon' },
        },
      ],
      total: 1,
    });
    wrapper.findComponent(ProjectSelectStub).vm.$emit('update:modelValue', 1);
    await flushPromises();
    const environmentSelect = wrapper.findComponent(
      '[data-test="project-environment-select"]',
    );
    expect(environmentSelect.exists()).toBe(true);
    environmentSelect.vm.$emit('update:modelValue', 12);
    await nextTick();

    expect(wrapper.text()).toContain('isilon-1');
    expect(wrapper.findComponent(VolumeSelectStub).exists()).toBe(true);
    expect(wrapper.findComponent(VolumeSelectStub).props('storageClusterId')).toBe(102);
    expect(wrapper.findComponent(QtreeSelectStub).exists()).toBe(false);
    expect(wrapper.findComponent('[data-test="storage-target-type"]').exists()).toBe(false);

    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/group/components/GroupFormDialog.vue'),
      'utf8',
    );
    expect(source).not.toContain('<StorageClusterSelect');
    expect(source).not.toContain('v-model="model.storage_cluster_id"');
  });
});
