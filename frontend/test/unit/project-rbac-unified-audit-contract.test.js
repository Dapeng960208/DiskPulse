import { defineComponent, h } from 'vue';
import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { aiApi, breadcrumbs, groupApi, projectApi } = vi.hoisted(() => ({
  aiApi: {
    createConversation: vi.fn(),
    listConversations: vi.fn(),
    listModels: vi.fn(),
  },
  breadcrumbs: { setDetailTitle: vi.fn() },
  groupApi: { fetch: vi.fn() },
  projectApi: { fetchById: vi.fn() },
}));

vi.mock('@/api/ai-api', () => ({ default: aiApi }));
vi.mock('@/api/group-api.js', () => ({ default: groupApi }));
vi.mock('@/api/project-api.js', () => ({ default: projectApi }));
vi.mock('@/stores/breadcrumbs', () => ({ useBreadcrumbs: () => breadcrumbs }));
vi.mock('vue-router', () => ({
  useRoute: () => ({ name: 'ProjectDetail', params: { id: '7' } }),
}));
vi.mock('@/api/support/base-request', () => ({ default: {} }));

const passthrough = (name) => defineComponent({
  name,
  setup(_, { slots }) {
    return () => h('div', slots.default?.());
  },
});

const tabPane = defineComponent({
  name: 'ElTabPane',
  props: { label: String },
  setup(props, { slots }) {
    return () => h('section', [props.label, slots.default?.()]);
  },
});

vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessage: { error: vi.fn(), warning: vi.fn() },
}));

const { default: BaseApi } = await import('@/api/support/base-api');
const { default: AiChatPage } = await import('@/pages/ai/AiChatPage.vue');
const { default: ProjectDetailPage } = await import('@/pages/project/ProjectDetailPage.vue');

describe('project RBAC and unified audit frontend contract', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiApi.listModels.mockResolvedValue([{ id: 3, name: 'project model' }]);
    aiApi.listConversations.mockResolvedValue([]);
    aiApi.createConversation.mockResolvedValue({ id: 19, model_id: 3, project_id: 24, title: '新对话' });
    groupApi.fetch.mockResolvedValue({ content: [] });
    projectApi.fetchById.mockResolvedValue({
      id: 7,
      name: 'project-a',
      capabilities: { manage_members: true, view_audit_events: true },
    });
  });

  it('shows member management and project audit tabs for an authorized project administrator', async () => {
    const wrapper = shallowMount(ProjectDetailPage, {
      global: {
        stubs: {
          ElTabs: passthrough('ElTabs'),
          ElTabPane: tabPane,
          StorageTypeTag: true,
        },
      },
    });
    await flushPromises();

    expect(wrapper.text()).toContain('成员');
    expect(wrapper.text()).toContain('项目审计');
  });

  it('exposes list and detail routes through a dedicated unified audit API client', async () => {
    const getSpy = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({});
    const clientPath = '@/api/audit-events-api.js';
    try {
      const { default: auditEventsApi } = await import(/* @vite-ignore */ clientPath);

      await auditEventsApi.fetch({ page: 2, size: 20, outcome: 'denied' });
      await auditEventsApi.fetchById('event-7');

      expect(auditEventsApi.urlPrefix).toBe('/audit-events');
      expect(getSpy).toHaveBeenCalledWith('', { page: 2, size: 20, outcome: 'denied' });
      expect(getSpy).toHaveBeenCalledWith('/event-7');
    } finally {
      getSpy.mockRestore();
    }
  });

  it('includes the selected project when creating an AI conversation', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.selectedProjectId = 24;

    await wrapper.vm.createConversation();

    expect(aiApi.createConversation).toHaveBeenCalledWith({
      title: '新对话',
      model_id: 3,
      project_id: 24,
    });
  });
});
