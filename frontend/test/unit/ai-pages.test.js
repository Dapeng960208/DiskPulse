import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const { aiApi, router } = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  aiApi: {
    listModels: vi.fn(),
    listConversations: vi.fn(),
    createConversation: vi.fn(),
    getConversation: vi.fn(),
    deleteConversation: vi.fn(),
    streamMessage: vi.fn(),
    listAdminModels: vi.fn(),
    createModel: vi.fn(),
    updateModel: vi.fn(),
    deleteModel: vi.fn(),
    testModel: vi.fn(),
    listAudits: vi.fn(),
    getAudit: vi.fn(),
  },
}));

vi.mock('@/api/ai-api', () => ({ default: aiApi }));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, params: { id: '9' } }),
  useRouter: () => router,
}));

const { default: AiChatPage } = await import('@/pages/ai/AiChatPage.vue');
const { default: AiCenterPage } = await import('@/pages/admin/ai/AiCenterPage.vue');

describe('AI pages interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiApi.listModels.mockResolvedValue([{ id: 1, name: 'Primary' }]);
    aiApi.listConversations.mockResolvedValue([]);
    aiApi.createConversation.mockResolvedValue({ id: 10, model_id: 1, title: '新对话' });
    aiApi.getConversation.mockResolvedValue({ id: 10, model_id: 1, title: '旧会话', messages: [] });
    aiApi.deleteConversation.mockResolvedValue();
    aiApi.listAdminModels.mockResolvedValue([{ id: 2, name: 'Admin Model', provider: 'openai', model: 'gpt' }]);
    aiApi.listAudits.mockResolvedValue({ content: [{ id: 7, status: 'succeeded' }], total: 1 });
    aiApi.createModel.mockResolvedValue({});
    aiApi.updateModel.mockResolvedValue({});
    aiApi.deleteModel.mockResolvedValue();
    aiApi.testModel.mockResolvedValue({ message: '连接成功', reply: 'OK' });
  });

  it('handles stream events, ignores stale events, deletes conversations, and retries failures', async () => {
    aiApi.streamMessage.mockImplementation(async (_id, _content, { onEvent }) => {
      onEvent({ event: 'user_message', data: { message: { id: 1, role: 'user', content: '容量？' }, conversation: { id: 10, title: '容量？', model_id: 1 } } });
      onEvent({ event: 'status', data: { status: 'thinking' } });
      onEvent({ event: 'tool_call_started', data: { tool_name: 'list_volumes' } });
      onEvent({ event: 'tool_call_finished', data: { tool_name: 'list_volumes', status: 'succeeded' } });
      onEvent({ event: 'delta', data: { text: '正常' } });
      onEvent({ event: 'completed', data: { message: { id: 2, role: 'assistant', content: '正常' }, conversation: { id: 10, title: '容量？', model_id: 1 } } });
    });
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.content = '容量？';
    await wrapper.vm.send();

    expect(wrapper.vm.messages.map((item) => item.role)).toEqual(['user', 'assistant']);
    expect(wrapper.vm.toolStatus[0].status).toBe('succeeded');
    wrapper.vm.applyEvent(999, { event: 'delta', data: { text: '旧消息' } });
    expect(wrapper.vm.messages.at(-1).content).toBe('正常');

    await wrapper.vm.removeConversation(10);
    expect(wrapper.vm.activeConversationId).toBeNull();

    aiApi.streamMessage.mockRejectedValueOnce(new Error('provider failed'));
    wrapper.vm.content = '重试内容';
    await wrapper.vm.send();
    expect(wrapper.vm.failedContent).toBe('重试内容');
    aiApi.streamMessage.mockResolvedValueOnce();
    await wrapper.vm.retry();
    expect(aiApi.streamMessage).toHaveBeenCalledTimes(3);
  });

  it('aborts an active generation and opens an existing conversation', async () => {
    let finish;
    aiApi.listConversations.mockResolvedValue([{ id: 10, model_id: 1, title: '旧会话' }]);
    aiApi.streamMessage.mockImplementation((_id, _content, { signal }) => new Promise((resolve) => {
      finish = () => {
        expect(signal.aborted).toBe(true);
        resolve();
      };
    }));
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    expect(aiApi.getConversation).toHaveBeenCalledWith(10);
    wrapper.vm.content = '停止';
    const sending = wrapper.vm.send();
    await flushPromises();
    wrapper.vm.stop();
    finish();
    await sending;
    expect(wrapper.vm.streaming).toBe(false);
  });

  it('creates, updates, tests, deletes models and loads audit filters', async () => {
    const wrapper = shallowMount(AiCenterPage);
    await flushPromises();
    wrapper.vm.addModel();
    wrapper.vm.form.name = 'New Model';
    wrapper.vm.form.model = 'gpt-test';
    await wrapper.vm.saveModel();
    expect(aiApi.createModel).toHaveBeenCalled();

    wrapper.vm.editModel({
      id: 2, name: 'Admin Model', provider: 'openai', model: 'gpt', enabled: true,
      enable_chat: true, temperature: 0.2, max_tokens: 100, api_key_masked: '****',
    });
    await wrapper.vm.saveModel();
    expect(aiApi.updateModel).toHaveBeenCalledWith(2, expect.not.objectContaining({ api_key: expect.anything() }));
    await wrapper.vm.testModel({ id: 2 });
    await wrapper.vm.deleteModel({ id: 2 });
    expect(aiApi.testModel).toHaveBeenCalledWith(2);
    expect(aiApi.deleteModel).toHaveBeenCalledWith(2);

    wrapper.vm.activeTab = 'audit';
    await flushPromises();
    expect(aiApi.listAudits).toHaveBeenCalled();
    wrapper.vm.openAudit({ id: 7 });
    expect(router.push).toHaveBeenCalledWith('/admin/ai-center/audits/7');
    expect(wrapper.vm.statusType('failed')).toBe('danger');
  });
});
