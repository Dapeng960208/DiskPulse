import { flushPromises, shallowMount } from '@vue/test-utils';
import { toRaw } from 'vue';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { commonDirectives } from '../helpers/mount';

const { aiApi, currentUser, router } = vi.hoisted(() => ({
  currentUser: {
    avatarUrl: 'https://example.test/current-user.png',
    displayName: '当前用户',
    username: 'current-user',
  },
  router: { push: vi.fn(), replace: vi.fn() },
  aiApi: {
    listModels: vi.fn(),
    listConversations: vi.fn(),
    createConversation: vi.fn(),
    getConversation: vi.fn(),
    deleteConversation: vi.fn(),
    decideQuotaConfirmation: vi.fn(),
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
vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => currentUser,
}));

const { default: AiChatPage } = await import('@/pages/ai/AiChatPage.vue');
const { default: AiCenterPage } = await import('@/pages/admin/ai/AiCenterPage.vue');

describe('AI pages interactions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiApi.streamMessage.mockReset();
    aiApi.streamMessage.mockResolvedValue();
    aiApi.listModels.mockResolvedValue([{ id: 1, name: 'Primary' }]);
    aiApi.listConversations.mockResolvedValue([]);
    aiApi.createConversation.mockResolvedValue({ id: 10, model_id: 1, title: '新对话' });
    aiApi.getConversation.mockResolvedValue({ id: 10, model_id: 1, title: '旧会话', messages: [] });
    aiApi.deleteConversation.mockResolvedValue();
    aiApi.decideQuotaConfirmation.mockResolvedValue({ decision: 'confirm', result: { ok: true, data: {} } });
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

  it('restores a persisted quota confirmation card when opening conversation history', async () => {
    // Review source: quota confirmation existed only in the live SSE event.
    // Resolution contract: the safe confirmation payload returned by history
    // renders through the same card without a second stream request.
    aiApi.listConversations.mockResolvedValue([{ id: 10, model_id: 1, title: '配额确认' }]);
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 1,
      title: '配额确认',
      messages: [{
        id: 2,
        role: 'assistant',
        content: '请确认',
        status: 'awaiting_confirmation',
        tool_calls: [],
        quota_confirmation: {
          confirmation_id: 'confirmation-owner-only',
          expires_at: 4102444800,
          expires_in_seconds: 300,
          preview: { resource: 'project-alpha', old_hard_limit: 100, new_hard_limit: 200, unit: 'GB' },
        },
      }],
    });

    const wrapper = shallowMount(AiChatPage);
    await flushPromises();

    expect(wrapper.vm.messages[0].quota_confirmation.confirmation_id).toBe('confirmation-owner-only');
    expect(wrapper.vm.messages[0].status).toBe('awaiting_confirmation');
  });

  it('shows whether a confirmed AI quota expansion succeeded or failed', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 8,
      role: 'assistant',
      status: 'awaiting_confirmation',
      tool_calls: [{ call_id: 'quota-1', tool_name: 'adjust_storage_usage_quota', status: 'awaiting_confirmation' }],
      quota_confirmation: {
        confirmation_id: 'quota-confirmation',
        deciding: false,
        decided: null,
        error: '',
        preview: { resource: '/data/alice', old_hard_limit: 100, new_hard_limit: 120, unit: 'GiB' },
      },
    }];

    await wrapper.vm.decideQuotaConfirmation(wrapper.vm.messages[0], 'confirm');

    expect(aiApi.decideQuotaConfirmation).toHaveBeenCalledWith(10, 'quota-confirmation', 'confirm');
    expect(wrapper.vm.messages[0].quota_confirmation.feedback).toEqual({
      type: 'success',
      text: '配额调整成功',
    });
    expect(wrapper.vm.messages[0].tool_calls[0]).toEqual(expect.objectContaining({ status: 'succeeded' }));

    aiApi.decideQuotaConfirmation.mockResolvedValueOnce({
      decision: 'confirm',
      result: { ok: false, error: '设备拒绝写入' },
    });
    wrapper.vm.messages[0].quota_confirmation = {
      confirmation_id: 'quota-confirmation-2',
      deciding: false,
      decided: null,
      error: '',
      preview: { resource: '/data/alice', old_hard_limit: 100, new_hard_limit: 120, unit: 'GiB' },
    };
    wrapper.vm.messages[0].tool_calls = [{ call_id: 'quota-2', tool_name: 'adjust_storage_usage_quota', status: 'awaiting_confirmation' }];

    await wrapper.vm.decideQuotaConfirmation(wrapper.vm.messages[0], 'confirm');

    expect(wrapper.vm.messages[0].quota_confirmation.feedback).toEqual({
      type: 'danger',
      text: '设备拒绝写入',
    });
    expect(wrapper.vm.messages[0].tool_calls[0]).toEqual(expect.objectContaining({ status: 'failed' }));
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

  it('labels a duplicate successful query as a reused result', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();

    expect(wrapper.vm.toolStatusText('reused')).toBe('复用已获取结果');
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

  it('renders a recovery action for a completed degraded assistant reply', async () => {
    const wrapper = shallowMount(AiChatPage, {
      global: {
        stubs: {
          ElScrollbar: { template: '<div class="el-scrollbar-stub"><slot /></div>' },
        },
      },
    });
    await flushPromises();
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 36,
      role: 'assistant',
      content: '正在整理已查询的数据',
      turn_id: 'turn-degraded',
      status: 'streaming',
      tool_calls: [{ call_id: 'call-projects', tool_name: 'list_projects', status: 'succeeded', result: { total: 4 } }],
    }];

    wrapper.vm.applyEvent(10, {
      event: 'completed',
      data: {
        turn_id: 'turn-degraded',
        message: {
          id: 36,
          role: 'assistant',
          content: '已根据当前查询结果回答。若需继续查询，请授权继续。',
          turn_id: 'turn-degraded',
          status: 'degraded',
          recovery: {
            reason: 'tool_iteration_limit',
            action: 'continue',
            label: '继续查询',
          },
          tool_calls: [{ call_id: 'call-projects', tool_name: 'list_projects', status: 'succeeded', result: { total: 4 } }],
        },
        conversation: { id: 10, title: '项目', model_id: 1 },
      },
    });
    await flushPromises();

    expect(wrapper.vm.messages[0]).toEqual(expect.objectContaining({
      status: 'degraded',
      recovery: expect.objectContaining({ action: 'continue', label: '继续查询' }),
    }));
    expect(wrapper.find('.tool-trace').exists()).toBe(true);
    expect(wrapper.find('[aria-label="继续查询"]').exists()).toBe(true);
  });

  it('sends a visible authorization message when the recovery action is selected', async () => {
    aiApi.streamMessage.mockImplementationOnce(async (_conversationId, prompt, { onEvent }) => {
      onEvent({
        event: 'user_message',
        data: {
          message: { id: 37, role: 'user', content: prompt },
          conversation: { id: 10, title: '项目', model_id: 1 },
        },
      });
      onEvent({
        event: 'accepted',
        data: {
          turn_id: 'turn-authorized-recovery',
          message: { id: 38, role: 'assistant', content: '', turn_id: 'turn-authorized-recovery', status: 'streaming', tool_calls: [] },
        },
      });
      onEvent({
        event: 'completed',
        data: {
          turn_id: 'turn-authorized-recovery',
          message: { id: 38, role: 'assistant', content: '已继续查询。', turn_id: 'turn-authorized-recovery', status: 'succeeded', tool_calls: [] },
          conversation: { id: 10, title: '项目', model_id: 1 },
        },
      });
    });
    const wrapper = shallowMount(AiChatPage, {
      global: {
        stubs: {
          ElScrollbar: { template: '<div class="el-scrollbar-stub"><slot /></div>' },
        },
      },
    });
    await flushPromises();
    wrapper.vm.conversations = [{ id: 10, model_id: 1, title: '项目' }];
    wrapper.vm.activeConversationId = 10;
    wrapper.vm.messages = [{
      id: 36,
      role: 'assistant',
      content: '本轮查询已达到上限。',
      turn_id: 'turn-degraded',
      status: 'degraded',
      recovery: {
        reason: 'tool_iteration_limit',
        action: 'continue',
        label: '继续查询',
      },
      tool_calls: [],
    }];
    await flushPromises();

    await wrapper.find('[aria-label="继续查询"]').trigger('click');
    await flushPromises();

    expect(aiApi.streamMessage).toHaveBeenCalledWith(
      10,
      expect.stringContaining('继续查询'),
      expect.objectContaining({ onEvent: expect.any(Function) }),
    );
    const authorizationPrompt = aiApi.streamMessage.mock.calls[0][1];
    expect(wrapper.findAll('.message.user').some((message) => message.text().includes(authorizationPrompt))).toBe(true);
    expect(wrapper.vm.messages.at(-1)).toEqual(expect.objectContaining({
      role: 'assistant',
      status: 'succeeded',
      content: '已继续查询。',
    }));
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

  it('turns an accepted but truncated stream into a retryable assistant failure', async () => {
    aiApi.listConversations.mockResolvedValue([{ id: 10, model_id: 1, title: '旧会话' }]);
    aiApi.streamMessage.mockImplementationOnce(async (_id, _content, { onEvent }) => {
      onEvent({
        event: 'accepted',
        data: {
          turn_id: 'turn-truncated',
          message: { id: 63, role: 'assistant', content: '', turn_id: 'turn-truncated', status: 'streaming', tool_calls: [] },
        },
      });
      onEvent({ event: 'delta', data: { turn_id: 'turn-truncated', text: '已获得部分结果' } });
      throw new Error('AI 流式响应未正常结束');
    });
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();
    wrapper.vm.content = '查询未完成的结果';

    await wrapper.vm.send();

    const assistant = wrapper.vm.messages.find((item) => item.turn_id === 'turn-truncated');
    expect(wrapper.vm.streaming).toBe(false);
    expect(assistant).toEqual(expect.objectContaining({
      status: 'failed',
      content: '已获得部分结果',
      error: 'AI 流式响应未正常结束',
    }));
    expect(wrapper.vm.failedContent).toBe('查询未完成的结果');
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

  it('keeps the workspace regions stable and sends from the input field action', async () => {
    const wrapper = shallowMount(AiChatPage, {
      global: {
        stubs: {
          ElScrollbar: { template: '<div class="el-scrollbar-stub"><slot /></div>' },
        },
      },
    });
    await flushPromises();

    expect(wrapper.find('.conversation-panel').exists()).toBe(true);
    expect(wrapper.find('.chat-heading').exists()).toBe(true);
    expect(wrapper.find('.message-list').exists()).toBe(true);
    expect(wrapper.find('.composer__notice').text()).toContain('AI 可能会出错');
    expect(wrapper.find('.composer__send').attributes('aria-label')).toBe('发送消息');
    expect(wrapper.find('.composer-actions').exists()).toBe(false);
  });

  it('uses the header avatar source for user messages and top-aligns message rows', async () => {
    const wrapper = shallowMount(AiChatPage, {
      global: {
        stubs: {
          ElScrollbar: { template: '<div><slot /></div>' },
          UserAvatar: {
            props: ['size', 'src'],
            template: '<img class="user-avatar" :src="src" :data-size="size" />',
          },
        },
      },
    });
    await flushPromises();
    wrapper.vm.messages = [
      { id: 81, role: 'user', content: '你好' },
      { id: 82, role: 'assistant', content: '你好，我可以协助分析容量。' },
    ];
    await flushPromises();

    expect(wrapper.find('.message-avatar--user').attributes('src')).toBe(currentUser.avatarUrl);
    expect(wrapper.find('.message-avatar--user').attributes('data-size')).toBe('32');
    expect(wrapper.find('.message-avatar--user').attributes('aria-label')).toBe('你的头像');
    expect(wrapper.find('.message-avatar--assistant').attributes('aria-label')).toBe('AI 助手头像');
    expect(wrapper.find('.message-avatar--assistant .message-avatar__pulse').exists()).toBe(true);
    const source = readFileSync(resolve(process.cwd(), 'src/pages/ai/AiChatPage.vue'), 'utf8');
    expect(source).toContain('--message-avatar-size: 32px;');
    expect(source).toMatch(/\.message\s*\{[^}]*align-items:\s*start;/);
  });

  it('keeps model selection beside the composer action and simplifies chat chrome', async () => {
    const wrapper = shallowMount(AiChatPage);
    await flushPromises();

    expect(wrapper.find('.panel-heading').text()).toContain('对话历史');
    expect(wrapper.find('.conversation-create').attributes('aria-label')).toBe('新建对话');
    expect(wrapper.find('.conversation-panel > .model-select').exists()).toBe(false);
    expect(wrapper.find('.composer__model').exists()).toBe(true);
    expect(wrapper.find('.chat-heading small').exists()).toBe(false);
  });

  it('constrains long chat history to the message scroller and gives the composer a visible border', async () => {
    const source = readFileSync(resolve(process.cwd(), 'src/pages/ai/AiChatPage.vue'), 'utf8');
    const appLayoutSource = readFileSync(resolve(process.cwd(), 'src/layouts/AppLayout.vue'), 'utf8');

    expect(source).toContain('flex: 1 1 0;');
    expect(source).toContain('height: 100%;');
    expect(source).toContain('border: 1px solid var(--text-tertiary);');
    expect(appLayoutSource).toContain('class="flex-1 min-h-0 flex flex-col"');
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

  it('renders readable audit summaries without a redundant page heading', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/pages/admin/ai/AiCenterPage.vue'), 'utf8');

    expect(source).not.toContain('<h2>AI 中心</h2>');
    expect(source).not.toContain('统一管理模型连接和对话审计，仅超级管理员可访问。');
    expect(source).toContain('row.conversation?.title');
    expect(source).toContain('row.user?.rd_username');
    expect(source).toContain('row.model?.name');
    expect(source).toContain('row.tool_names?.join');
  });
});
