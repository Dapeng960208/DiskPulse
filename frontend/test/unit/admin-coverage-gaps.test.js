import { flushPromises, shallowMount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const projectApi = { fetchById: vi.fn() };
const groupApi = { fetch: vi.fn() };

vi.mock('@/api/project-api.js', () => ({ default: projectApi }));
vi.mock('@/api/group-api.js', () => ({ default: groupApi }));

describe('admin coverage gaps', () => {
  it('loads the dashboard after a project is selected', async () => {
    projectApi.fetchById.mockResolvedValue({ id: 7, name: '项目 A', used: 10, limit: 20 });
    groupApi.fetch.mockResolvedValue({
      content: [{ id: 8, name: '项目组 A', used: 3, limit: 5 }],
    });

    const { default: DashboardPage } = await import('@/pages/dashboard/DashboardPage.vue');
    const wrapper = shallowMount(DashboardPage);
    await wrapper.findComponent({ name: 'ProjectSelect' }).vm.$emit('update:modelValue', 7);
    await flushPromises();

    expect(projectApi.fetchById).toHaveBeenCalledWith(7);
    expect(wrapper.findComponent({ name: 'PieCharts' }).exists()).toBe(true);
  });
});
