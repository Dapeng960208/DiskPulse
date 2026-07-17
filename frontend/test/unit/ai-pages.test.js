import { flushPromises, shallowMount } from '@vue/test-utils';
import { toRaw } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { commonDirectives } from '../helpers/mount';

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

  it('ignores stale events, deletes conversations, and retries failures', async () => {
    aiApi.streamMessage.mockImplementation(async (_id, _content, { onEvent }) => {
      onEvent({ event: 'user_message', data: { message: { id: 1, role: 'user', content: '容量？' }, conversation: { id: 10, title: '容量？', model_id: 1 } } });
      onEvent({ event: 'status', data: { status: 'thinking' } });
      onEvent({ event: 'accepted', data: { turn_id: 'turn-retry', message: { id: 2, role: 'assistant', content: '', turn_id: 'turn-retry', status: 'streaming', tool_calls: [] } } });
      onEvent({ event: 'delta', data: { turn_id: 'turn-retry', text: '正常' } });
      onEvent({ event: 'completed', data: { turn_id: 'turn-retry', message: { id: 2, role: 'assistant', content: '正常', turn_id: 'turn-retry', status: 'succeeded', tool_calls: [] }, conversation: { id: 10, title: '容量？', model_id: 1 } } });
    });
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.content = '容量？';
    await wrapper.vm.send();

    expect(wrapper.vm.messages.map((item) => item.role)).toEqual(['user', 'assistant']);
    wrapper.vm.applyEvent(999, { event: 'delta', data: { turn_id: 'turn-retry', text: '旧消息' } });
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

  it('streams text and tool status into the assistant message accepted for its turn', async () => {
    const acceptedMessage = {
      id: 12,
      role: 'assistant',
      content: '',
      turn_id: 'turn-stream',
      status: 'streaming',
      tool_calls: [],
    };
    aiApi.streamMessage.mockImplementation(async (_id, _content, { onEvent }) => {
      onEvent({ event: 'user_message', data: { message: { id: 11, role: 'user', content: '查询卷' }, conversation: { id: 10, title: '查询卷', model_id: 1 } } });
      onEvent({ event: 'accepted', data: { turn_id: 'turn-stream', message: acceptedMessage } });
      onEvent({ event: 'tool_call_started', data: { turn_id: 'turn-stream', call_id: 'call-volume', tool_name: 'list_volumes', arguments: { project: 'alpha' } } });
      onEvent({ event: 'delta', data: { turn_id: 'turn-stream', text: '已查询到卷。' } });
    });
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.content = '查询卷';
    await wrapper.vm.send();

    const assistant = wrapper.vm.messages.find((item) => item.role === 'assistant');
    expect(toRaw(assistant)).toBe(acceptedMessage);
    expect(assistant.content).toBe('已查询到卷。');
    expect(assistant.tool_calls).toEqual([
      expect.objectContaining({
        call_id: 'call-volume',
        tool_name: 'list_volumes',
        status: 'running',
        arguments: { project: 'alpha' },
      }),
    ]);
  });

  it('matches duplicate tool names by call_id within the accepted assistant reply', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 22,
      role: 'assistant',
      content: '',
      turn_id: 'turn-duplicate-tools',
      status: 'streaming',
      tool_calls: [],
    }];

    wrapper.vm.applyEvent(10, { event: 'tool_call_started', data: { turn_id: 'turn-duplicate-tools', call_id: 'call-first', tool_name: 'list_volumes', arguments: { project: 'first' } } });
    wrapper.vm.applyEvent(10, { event: 'tool_call_started', data: { turn_id: 'turn-duplicate-tools', call_id: 'call-second', tool_name: 'list_volumes', arguments: { project: 'second' } } });
    wrapper.vm.applyEvent(10, { event: 'tool_call_finished', data: { turn_id: 'turn-duplicate-tools', call_id: 'call-second', tool_name: 'list_volumes', status: 'succeeded', elapsed_ms: 148, result: { total: 2 } } });

    expect(wrapper.vm.messages[0].tool_calls).toEqual([
      expect.objectContaining({ call_id: 'call-first', status: 'running', arguments: { project: 'first' } }),
      expect.objectContaining({ call_id: 'call-second', status: 'succeeded', elapsed_ms: 148, result: { total: 2 } }),
    ]);
  });

  it('reconciles a completed message in place and preserves expanded tool details', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 32,
      role: 'assistant',
      content: '部分回答',
      turn_id: 'turn-completed',
      status: 'streaming',
      streaming: true,
      tool_calls: [{ call_id: 'call-expanded', tool_name: 'list_projects', status: 'running', expanded: true }],
    }];
    const streamedMessage = wrapper.vm.messages[0];

    wrapper.vm.applyEvent(10, {
      event: 'completed',
      data: {
        turn_id: 'turn-completed',
        message: {
          id: 32,
          role: 'assistant',
          content: '完整回答',
          turn_id: 'turn-completed',
          status: 'succeeded',
          tool_calls: [{ call_id: 'call-expanded', tool_name: 'list_projects', status: 'succeeded', elapsed_ms: 71, result: { total: 4 } }],
        },
        conversation: { id: 10, title: '项目', model_id: 1 },
      },
    });

    expect(wrapper.vm.messages[0]).toBe(streamedMessage);
    expect(streamedMessage.content).toBe('完整回答');
    expect(streamedMessage.tool_calls[0]).toEqual(expect.objectContaining({ status: 'succeeded', expanded: true, elapsed_ms: 71 }));
  });

  it('rehydrates persisted tool traces beneath their historical assistant reply', async () => {
    aiApi.listConversations.mockResolvedValue([{ id: 10, model_id: 1, title: '历史对话' }]);
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 1,
      title: '历史对话',
      messages: [
        { id: 41, role: 'user', content: '有多少项目' },
        {
          id: 42,
          role: 'assistant',
          content: '当前共有 4 个项目。',
          turn_id: 'turn-history',
          status: 'succeeded',
          tool_calls: [{
            call_id: 'call-history',
            tool_name: 'list_projects',
            status: 'succeeded',
            elapsed_ms: 83,
            arguments: { active_only: true },
            result: { total: 4 },
            truncated: true,
          }],
        },
        { id: 43, role: 'assistant', content: '旧版历史消息' },
      ],
    });

    const wrapper = shallowMount(AiChatPage, {
      global: {
        stubs: {
          ElScrollbar: { template: '<div class="el-scrollbar-stub"><slot /></div>' },
        },
      },
    });
    await flushPromises();

    expect(wrapper.findAll('.tool-trace')).toHaveLength(1);
    expect(wrapper.text()).toContain('list_projects');
    expect(wrapper.text()).toContain('结果已截断');
  });

  it('keeps partial text and tool results when a turn is cancelled', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 52,
      role: 'assistant',
      content: '已完成部分查询',
      turn_id: 'turn-cancelled',
      status: 'streaming',
      tool_calls: [{ call_id: 'call-complete', tool_name: 'list_alerts', status: 'succeeded', result: { total: 3 } }],
    }];
    const streamedMessage = wrapper.vm.messages[0];

    wrapper.vm.applyEvent(10, {
      event: 'cancelled',
      data: {
        turn_id: 'turn-cancelled',
        message: {
          id: 52,
          role: 'assistant',
          content: '已完成部分查询',
          turn_id: 'turn-cancelled',
          status: 'cancelled',
          tool_calls: [{ call_id: 'call-complete', tool_name: 'list_alerts', status: 'succeeded', result: { total: 3 } }],
        },
        conversation: { id: 10, title: '告警', model_id: 1 },
      },
    });

    expect(wrapper.vm.messages[0]).toBe(streamedMessage);
    expect(streamedMessage).toEqual(expect.objectContaining({ content: '已完成部分查询', status: 'cancelled' }));
    expect(streamedMessage.tool_calls[0].result).toEqual({ total: 3 });
  });

  it('keeps partial text and tool results when a turn fails', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 62,
      role: 'assistant',
      content: '已返回部分结果',
      turn_id: 'turn-failed',
      status: 'streaming',
      tool_calls: [{ call_id: 'call-failed', tool_name: 'list_qtrees', status: 'failed', result: { error: '访问失败' } }],
    }];
    const streamedMessage = wrapper.vm.messages[0];

    expect(() => wrapper.vm.applyEvent(10, {
      event: 'error',
      data: {
        turn_id: 'turn-failed',
        message: {
          id: 62,
          role: 'assistant',
          content: '已返回部分结果',
          turn_id: 'turn-failed',
          status: 'failed',
          tool_calls: [{ call_id: 'call-failed', tool_name: 'list_qtrees', status: 'failed', result: { error: '访问失败' } }],
        },
        conversation: { id: 10, title: 'Qtree', model_id: 1 },
        error: 'AI 服务请求失败',
      },
    })).not.toThrow();
    expect(wrapper.vm.messages[0]).toBe(streamedMessage);
    expect(streamedMessage).toEqual(expect.objectContaining({ content: '已返回部分结果', status: 'failed' }));
    expect(streamedMessage.tool_calls[0].result).toEqual({ error: '访问失败' });
  });

  it('locally marks an aborted accepted turn as cancelled without clearing partial content or tools', async () => {
    aiApi.listConversations.mockResolvedValue([{ id: 10, model_id: 1, title: '旧会话' }]);
    aiApi.streamMessage.mockImplementation((_id, _content, { signal, onEvent }) => {
      onEvent({ event: 'user_message', data: { message: { id: 71, role: 'user', content: '停止' }, conversation: { id: 10, title: '旧会话', model_id: 1 } } });
      onEvent({ event: 'accepted', data: { turn_id: 'turn-abort', message: { id: 72, role: 'assistant', content: '', turn_id: 'turn-abort', status: 'streaming', tool_calls: [] } } });
      onEvent({ event: 'tool_call_started', data: { turn_id: 'turn-abort', call_id: 'call-abort', tool_name: 'list_alerts', arguments: {} } });
      onEvent({ event: 'delta', data: { turn_id: 'turn-abort', text: '已获得部分结果' } });
      return new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => {
          expect(signal.aborted).toBe(true);
          const error = new Error('aborted');
          error.name = 'AbortError';
          reject(error);
        }, { once: true });
      });
    });
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    expect(aiApi.getConversation).toHaveBeenCalledWith(10);
    wrapper.vm.content = '停止';
    const sending = wrapper.vm.send();
    await flushPromises();
    const streamedMessage = wrapper.vm.messages.find((item) => item.turn_id === 'turn-abort');
    wrapper.vm.stop();
    await sending;

    expect(wrapper.vm.streaming).toBe(false);
    expect(wrapper.vm.messages.find((item) => item.turn_id === 'turn-abort')).toBe(streamedMessage);
    expect(streamedMessage).toEqual(expect.objectContaining({ content: '已获得部分结果', status: 'cancelled' }));
    expect(streamedMessage.tool_calls).toEqual([expect.objectContaining({ call_id: 'call-abort', status: 'running' })]);
  });

  it('creates, updates, tests, deletes models and loads audit filters', async () => {
    const wrapper = shallowMount(AiCenterPage, {
      global: { directives: commonDirectives },
    });
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
