import { flushPromises, shallowMount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { commonDirectives } from '../helpers/mount';

const { aiApi, currentUser, messageApi, router } = vi.hoisted(() => ({
  currentUser: {
    avatarUrl: '',
    displayName: '当前用户',
    username: 'current-user',
  },
  messageApi: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
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
    getConversationAudits: vi.fn(),
    getAiSettings: vi.fn(),
    updateAiSettings: vi.fn(),
    refreshModelCapabilities: vi.fn(),
  },
}));

vi.mock('@/api/ai-api', () => ({ default: aiApi }));
vi.mock('@/stores/current-user', () => ({
  useCurrentUser: () => currentUser,
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: {}, params: {} }),
  useRouter: () => router,
}));
vi.mock('element-plus', async (importOriginal) => ({
  ...(await importOriginal()),
  ElMessage: messageApi,
}));

const { default: AiChatPage } = await import('@/pages/ai/AiChatPage.vue');
const { default: AiCenterPage } = await import('@/pages/admin/ai/AiCenterPage.vue');

const reasoningControl = (kind, options = [], extra = {}) => ({
  kind,
  options,
  provider_default: extra.provider_default ?? null,
  mandatory: extra.mandatory ?? false,
  source: extra.source ?? 'official_catalog',
  status: extra.status ?? 'ready',
  updated_at: '2026-07-23T10:00:00Z',
});

const model = (id, name, control, extra = {}) => ({
  id,
  name,
  provider: extra.provider || 'openai',
  model: extra.model || `model-${id}`,
  enabled: true,
  enable_chat: true,
  is_default: extra.is_default ?? false,
  reasoning_control: control,
});

const passthrough = (name) => ({
  name,
  template: '<div><slot /></div>',
});

const DialogStub = {
  name: 'ElDialog',
  template: '<div><slot name="header" /><slot /><slot name="footer" /></div>',
};

const FormStub = {
  name: 'ElForm',
  template: '<form><slot /></form>',
};

const FormItemStub = {
  name: 'ElFormItem',
  template: '<label><slot /></label>',
};

const SelectStub = {
  name: 'ElSelect',
  inheritAttrs: false,
  props: {
    modelValue: { default: null },
    disabled: { type: Boolean, default: false },
  },
  emits: ['update:modelValue', 'change'],
  template: '<div v-bind="$attrs" :modelvalue="modelValue" :disabled="disabled"><slot /></div>',
};

const OptionStub = {
  name: 'ElOption',
  inheritAttrs: false,
  props: {
    label: { type: String, default: '' },
    value: { default: null },
  },
  template: '<span v-bind="$attrs" :label="label" :value="value">{{ label }}</span>',
};

const DataTable = {
  name: 'DataTable',
  props: {
    data: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    pagination: { type: Object, default: undefined },
  },
  emits: ['update:pagination'],
  template: '<div><slot /></div>',
};

const QueryForm = {
  name: 'QueryForm',
  emits: ['query', 'reset'],
  template: '<form><slot /></form>',
};

function mountAiCenter() {
  return shallowMount(AiCenterPage, {
    global: {
      directives: commonDirectives,
      stubs: {
        DataTable,
        QueryForm,
        ElDialog: DialogStub,
        ElForm: FormStub,
        ElFormItem: FormItemStub,
        ElOption: OptionStub,
        ElSelect: SelectStub,
        ElTabs: passthrough('ElTabs'),
        ElTabPane: passthrough('ElTabPane'),
      },
    },
  });
}

function mountAiChat() {
  return shallowMount(AiChatPage, {
    global: {
      stubs: {
        ElOption: OptionStub,
        ElSelect: SelectStub,
      },
    },
  });
}

describe('AI chat model defaults and reasoning controls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiApi.listModels.mockResolvedValue([
      model(1, '普通模型', reasoningControl('none')),
      model(
        2,
        '默认推理模型',
        reasoningControl('effort', ['minimal', 'low', 'medium', 'high', 'xhigh', 'max']),
        { is_default: true },
      ),
    ]);
    aiApi.listConversations.mockResolvedValue([]);
    aiApi.createConversation.mockResolvedValue({
      id: 10,
      model_id: 2,
      title: '新对话',
      messages: [],
    });
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 2,
      title: '已有会话',
      messages: [],
    });
    aiApi.streamMessage.mockResolvedValue();
  });

  it('prefers the administrator default model for a new conversation and falls back to the first available model', async () => {
    const wrapper = mountAiChat();
    await flushPromises();

    expect(wrapper.vm.selectedModelId).toBe(2);
    await wrapper.vm.createConversation();
    expect(aiApi.createConversation).toHaveBeenCalledWith({
      title: '新对话',
      model_id: 2,
    });

    aiApi.listModels.mockResolvedValue([
      model(7, '首个模型', reasoningControl('toggle', ['on', 'off'])),
      model(8, '备用模型', reasoningControl('none')),
    ]);
    aiApi.createConversation.mockResolvedValueOnce({
      id: 11,
      model_id: 7,
      title: '新对话',
      messages: [],
    });
    const fallbackWrapper = mountAiChat();
    await flushPromises();

    expect(fallbackWrapper.vm.selectedModelId).toBe(7);
    await fallbackWrapper.vm.createConversation();
    expect(aiApi.createConversation).toHaveBeenLastCalledWith({
      title: '新对话',
      model_id: 7,
    });
  });

  it('locks the model selector to the model stored on an existing conversation', async () => {
    aiApi.listConversations.mockResolvedValue([
      { id: 10, model_id: 1, title: '已有会话' },
    ]);
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 1,
      title: '已有会话',
      messages: [],
    });
    const wrapper = mountAiChat();
    await flushPromises();

    expect(wrapper.vm.selectedModelId).toBe(1);
    expect(wrapper.get('[aria-label="选择模型"]').attributes('disabled')).toBe('true');

    wrapper.vm.content = '继续当前会话';
    await wrapper.vm.send();
    expect(aiApi.createConversation).not.toHaveBeenCalled();
    expect(aiApi.streamMessage).toHaveBeenCalledWith(
      10,
      '继续当前会话',
      expect.objectContaining({ onEvent: expect.any(Function) }),
    );
  });

  it('renders effort options with the specified Chinese labels', async () => {
    const wrapper = mountAiChat();
    await flushPromises();

    const selector = wrapper.get('[aria-label="推理强度"]');
    expect(selector.attributes()).not.toHaveProperty('disabled');
    expect(
      selector.findAll('span').map((option) => ({
        label: option.attributes('label'),
        value: option.attributes('value'),
      })),
    ).toEqual([
      { label: '自动', value: 'auto' },
      { label: '极简', value: 'minimal' },
      { label: '轻度', value: 'low' },
      { label: '标准', value: 'medium' },
      { label: '深度', value: 'high' },
      { label: '超深度', value: 'xhigh' },
      { label: '最大', value: 'max' },
    ]);
  });

  it('renders toggle controls as auto/on/off and explains models without adjustable reasoning', async () => {
    aiApi.listModels.mockResolvedValue([
      model(3, '开关思考模型', reasoningControl('toggle', ['on', 'off']), { is_default: true }),
    ]);
    const toggleWrapper = mountAiChat();
    await flushPromises();

    const toggleSelector = toggleWrapper.get('[aria-label="思考模式"]');
    expect(toggleSelector.findAll('span').map((option) => option.attributes('label')))
      .toEqual(['自动', '开启', '关闭']);

    aiApi.listModels.mockResolvedValue([
      model(4, '普通模型', reasoningControl('none'), { is_default: true }),
    ]);
    const noneWrapper = mountAiChat();
    await flushPromises();

    expect(noneWrapper.get('[aria-label="推理设置"]').attributes('disabled')).toBe('true');
    expect(noneWrapper.text()).toContain('此模型不支持可调推理');
  });

  it('sends a reasoning value with each message and keeps it for the current conversation', async () => {
    aiApi.listConversations.mockResolvedValue([
      { id: 10, model_id: 2, title: '已有会话' },
    ]);
    const wrapper = mountAiChat();
    await flushPromises();
    wrapper.vm.selectedReasoning = 'high';
    wrapper.vm.content = '请深度分析';

    await wrapper.vm.send();

    expect(aiApi.streamMessage).toHaveBeenCalledWith(
      10,
      '请深度分析',
      expect.objectContaining({
        reasoning: 'high',
        onEvent: expect.any(Function),
      }),
    );
    expect(wrapper.vm.selectedReasoning).toBe('high');
  });

  it('restores reasoning from the latest user message in conversation history', async () => {
    aiApi.listConversations.mockResolvedValue([
      { id: 10, model_id: 2, title: '已有会话' },
    ]);
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 2,
      title: '已有会话',
      messages: [
        { id: 1, role: 'user', content: '第一次', reasoning: 'low' },
        { id: 2, role: 'assistant', content: '第一次回复' },
        { id: 3, role: 'user', content: '第二次', reasoning: 'high' },
        { id: 4, role: 'assistant', content: '第二次回复' },
      ],
    });

    const wrapper = mountAiChat();
    await flushPromises();

    expect(wrapper.vm.selectedReasoning).toBe('high');
  });

  it('falls back to auto and warns when a persisted reasoning value is no longer supported', async () => {
    aiApi.listModels.mockResolvedValue([
      model(
        2,
        '能力已变化',
        reasoningControl('effort', ['low', 'medium']),
        { is_default: true },
      ),
    ]);
    aiApi.listConversations.mockResolvedValue([
      { id: 10, model_id: 2, title: '已有会话' },
    ]);
    aiApi.getConversation.mockResolvedValue({
      id: 10,
      model_id: 2,
      title: '已有会话',
      messages: [
        { id: 1, role: 'user', content: '旧请求', reasoning: 'high' },
        { id: 2, role: 'assistant', content: '旧回复' },
      ],
    });

    const wrapper = mountAiChat();
    await flushPromises();

    expect(wrapper.vm.selectedReasoning).toBe('auto');
    expect(messageApi.warning).toHaveBeenCalledWith(expect.stringMatching(/推理.*自动/));
  });
});

describe('AI center default model and capability management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiApi.listAdminModels.mockResolvedValue([
      {
        ...model(2, '默认推理模型', reasoningControl('effort', ['low', 'medium', 'high'], {
          source: 'provider',
        }), { is_default: true }),
        base_url: 'https://api.openai.com/v1',
        capability_status: 'ready',
        capability_source: 'provider',
      },
    ]);
    aiApi.getAiSettings.mockResolvedValue({ default_chat_model_id: 2 });
    aiApi.updateAiSettings.mockResolvedValue({ default_chat_model_id: 2 });
    aiApi.refreshModelCapabilities.mockResolvedValue({
      model_id: 2,
      status: 'ready',
      source: 'provider',
    });
    aiApi.listAudits.mockResolvedValue({ content: [], total: 0 });
  });

  it('loads and updates the administrator default chat model', async () => {
    const wrapper = mountAiCenter();
    await flushPromises();

    expect(aiApi.getAiSettings).toHaveBeenCalledOnce();
    expect(wrapper.vm.defaultModelId).toBe(2);
    expect(wrapper.get('[aria-label="默认聊天模型"]').attributes('modelvalue')).toBe('2');

    await wrapper.vm.saveDefaultModel();
    expect(aiApi.updateAiSettings).toHaveBeenCalledWith({
      default_chat_model_id: 2,
    });
  });

  it('offers all branded provider presets and keeps the preset base URL editable', async () => {
    const wrapper = mountAiCenter();
    await flushPromises();
    wrapper.vm.addModel();
    await flushPromises();

    const providerSelect = wrapper.get('.model-provider-select');
    expect(providerSelect.findAll('span').map((option) => ({
      label: option.attributes('label'),
      value: option.attributes('value'),
    }))).toEqual([
      { label: 'OpenAI', value: 'openai' },
      { label: 'OpenRouter', value: 'openrouter' },
      { label: 'Ollama', value: 'ollama' },
      { label: 'Claude API', value: 'claude' },
      { label: 'Claude Code', value: 'claude_code' },
      { label: 'DeepSeek', value: 'deepseek' },
      { label: '通义千问', value: 'dashscope' },
      { label: '豆包', value: 'volcengine' },
      { label: '智谱 GLM', value: 'zhipu' },
      { label: 'Kimi', value: 'moonshot' },
      { label: 'MiniMax', value: 'minimax' },
      { label: '百度千帆', value: 'qianfan' },
      { label: '腾讯混元', value: 'hunyuan' },
    ]);

    await providerSelect.vm.$emit('update:modelValue', 'deepseek');
    await providerSelect.vm.$emit('change', 'deepseek');
    await flushPromises();
    expect(wrapper.vm.form).toMatchObject({
      provider: 'deepseek',
      base_url: expect.stringMatching(/^https:\/\//),
    });
    expect(wrapper.get('.model-base-url').attributes()).not.toHaveProperty('disabled');
  });

  it('maps capability status/source for display and refreshes one model on demand', async () => {
    const wrapper = mountAiCenter();
    await flushPromises();

    expect(wrapper.vm.capabilitySourceText('provider')).toBe('Provider 动态能力');
    expect(wrapper.vm.capabilitySourceText('official_catalog')).toBe('官方能力目录');
    expect(wrapper.vm.capabilitySourceText('unknown')).toBe('未知');
    expect(wrapper.vm.capabilityStatusText('ready')).toBe('已获取');
    expect(wrapper.vm.capabilityStatusText('failed')).toBe('获取失败');

    aiApi.listAdminModels.mockClear();
    await wrapper.vm.refreshCapabilities({ id: 2 });

    expect(aiApi.refreshModelCapabilities).toHaveBeenCalledWith(2);
    expect(aiApi.listAdminModels).toHaveBeenCalledOnce();
  });
});
