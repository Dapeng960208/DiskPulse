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

const { default: ProjectStorageDistribution } = await import('@/pages/project/components/ProjectStorageDistribution.vue');

const ElCard = defineComponent({
  name: 'ElCard',
  setup(_, { slots }) {
    return () => h('section', slots.default?.());
  },
});

let wrapper;

beforeEach(() => {
  mocks.fetchStorageTreeById.mockReset();
  mocks.fetchStorageTreeById.mockResolvedValue({ data: [{ name: '设计组', children: [{ name: 'alice' }] }] });
});

afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
});

describe('ProjectStorageDistribution', () => {
  it('loads current database usage as a project-group to user tree without a filter form', async () => {
    wrapper = shallowMount(ProjectStorageDistribution, {
      props: { projectId: 9 },
      global: {
        stubs: {
          ElCard,
          DiskUsage: { name: 'DiskUsage', props: ['data', 'height'], template: '<div />' },
          LoadingCharts: true,
          AnimatedTextChart: true,
        },
      },
    });
    await flushPromises();

    expect(mocks.fetchStorageTreeById).toHaveBeenCalledTimes(1);
    expect(mocks.fetchStorageTreeById).toHaveBeenLastCalledWith(9, { value_type: 'used' });
    expect(wrapper.find('form').exists()).toBe(false);
    expect(wrapper.getComponent({ name: 'DiskUsage' }).props('data')).toEqual([
      { name: '设计组', children: [{ name: 'alice' }] },
    ]);
    expect(wrapper.getComponent({ name: 'DiskUsage' }).props('height')).toBe('100%');
  });
});
