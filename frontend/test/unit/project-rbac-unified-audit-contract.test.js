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
vi.mock('@/utils/authorization', () => ({ hasRole: () => false }));
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
const { default: auditEventsApi } = await import('@/api/audit-events-api.js');
const { default: membershipApi } = await import('@/api/project-membership-api.js');
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

  it('does not expose member or audit tabs when the project omits those capabilities', async () => {
    projectApi.fetchById.mockResolvedValueOnce({ id: 7, name: 'project-a', capabilities: {} });
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

    expect(wrapper.text()).not.toContain('成员');
    expect(wrapper.text()).not.toContain('项目审计');
  });

  it('exposes list and detail routes through a dedicated unified audit API client', async () => {
    const getSpy = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({});
    try {
      await auditEventsApi.fetch({ page: 2, size: 20, outcome: 'denied' });
      await auditEventsApi.fetchById('event-7');

      expect(auditEventsApi.urlPrefix).toBe('/v1/audit-events');
      expect(getSpy).toHaveBeenCalledWith('', { page: 2, size: 20, outcome: 'denied' }, undefined);
      expect(getSpy).toHaveBeenCalledWith('/event-7', undefined, undefined);
    } finally {
      getSpy.mockRestore();
    }
  });

  it('creates an unassigned AI conversation without forcing a project identifier', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();

    await wrapper.vm.createConversation();

    expect(aiApi.createConversation).toHaveBeenCalledWith({
      title: '新对话',
      model_id: 3,
    });
  });

  it('maps member management operations to the project membership routes', async () => {
    const getSpy = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue([]);
    const postSpy = vi.spyOn(BaseApi.prototype, 'post').mockResolvedValue({});
    const patchSpy = vi.spyOn(BaseApi.prototype, 'patch').mockResolvedValue({});
    const deleteSpy = vi.spyOn(BaseApi.prototype, 'delete').mockResolvedValue();
    try {
      await membershipApi.list(7);
      await membershipApi.create(7, { user_id: 24, role: 'reader' });
      await membershipApi.update(7, 24, { role: 'editor' });
      await membershipApi.remove(7, 24);

      expect(getSpy).toHaveBeenCalledWith('/projects/7/members');
      expect(postSpy).toHaveBeenCalledWith('/projects/7/members', { user_id: 24, role: 'reader' });
      expect(patchSpy).toHaveBeenCalledWith('/projects/7/members/24', { role: 'editor' });
      expect(deleteSpy).toHaveBeenCalledWith('/projects/7/members/24');
    } finally {
      getSpy.mockRestore();
      postSpy.mockRestore();
      patchSpy.mockRestore();
      deleteSpy.mockRestore();
    }
  });
});
