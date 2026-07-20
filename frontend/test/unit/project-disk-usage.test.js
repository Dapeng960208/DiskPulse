import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  fetchStorageTreeById: vi.fn(),
}));

vi.mock('@/api/project-api.js', () => ({
  default: {
    fetchStorageTreeById: mocks.fetchStorageTreeById,
  },
}));

const { default: ProjectDiskUsage } = await import('@/pages/project/components/ProjectDiskUsage.vue');

const FilterForm = defineComponent({
  name: 'FilterForm',
  emits: ['query', 'reset'],
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

let wrapper;

beforeEach(() => {
  mocks.fetchStorageTreeById.mockReset();
  mocks.fetchStorageTreeById.mockResolvedValue({ data: [] });
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
});

describe('ProjectDiskUsage', () => {
  it('resets the project overview to project 1 when attributeId is absent', async () => {
    wrapper = shallowMount(ProjectDiskUsage, {
      global: {
        stubs: {
          FilterForm,
          QueryForm: FilterForm,
        },
      },
    });
    await flushPromises();

    expect(mocks.fetchStorageTreeById).toHaveBeenLastCalledWith(1, { value_type: 'limit' });

    mocks.fetchStorageTreeById.mockClear();
    wrapper.findComponent({ name: 'FilterForm' }).vm.$emit('reset');
    await flushPromises();

    expect(mocks.fetchStorageTreeById).toHaveBeenCalledOnce();
    expect(mocks.fetchStorageTreeById).toHaveBeenLastCalledWith(1, { value_type: 'limit' });
  });
});
