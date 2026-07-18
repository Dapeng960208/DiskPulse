<script setup>
import { computed, nextTick, onMounted, ref } from 'vue';
import {
  ElButton,
  ElEmpty,
  ElInput,
  ElMessage,
  ElOption,
  ElPopconfirm,
  ElScrollbar,
  ElSelect,
} from 'element-plus';
import aiApi from '@/api/ai-api';
import { renderAiMarkdown } from '@/services/ai-markdown';

const models = ref([]);
const conversations = ref([]);
const activeConversationId = ref(null);
const selectedModelId = ref(null);
const messages = ref([]);
const content = ref('');
const failedContent = ref('');
const streaming = ref(false);
const streamStatus = ref('');
const activeTurnId = ref(null);
const autoFollowMessages = ref(true);
const messageScroll = ref();
let abortController = null;
let activePrompt = '';

const activeConversation = computed(() => conversations.value.find((item) => item.id === activeConversationId.value));

async function loadInitial() {
  try {
    [models.value, conversations.value] = await Promise.all([
      aiApi.listModels(),
      aiApi.listConversations(),
    ]);
    selectedModelId.value = models.value[0]?.id || null;
    if (conversations.value.length) await openConversation(conversations.value[0].id);
  } catch {
    ElMessage.error('AI 助手加载失败');
  }
}

async function createConversation() {
  if (!selectedModelId.value) {
    ElMessage.warning('当前没有可用模型，请联系超级管理员');
    return null;
  }
  const conversation = await aiApi.createConversation({ title: '新对话', model_id: selectedModelId.value });
  conversations.value.unshift(conversation);
  activeConversationId.value = conversation.id;
  messages.value = [];
  autoFollowMessages.value = true;
  return conversation;
}

async function openConversation(id) {
  if (streaming.value) return;
  const conversation = await aiApi.getConversation(id);
  activeConversationId.value = id;
  selectedModelId.value = conversation.model_id;
  messages.value = conversation.messages || [];
  autoFollowMessages.value = true;
  await scrollToBottom(true);
}

async function removeConversation(id) {
  await aiApi.deleteConversation(id);
  conversations.value = conversations.value.filter((item) => item.id !== id);
  if (activeConversationId.value === id) {
    activeConversationId.value = null;
    messages.value = [];
  }
}

function isNearMessageListBottom() {
  const wrap = messageScroll.value?.wrapRef;
  if (!wrap) return true;
  return wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight <= 48;
}

function handleMessageScroll() {
  autoFollowMessages.value = isNearMessageListBottom();
}

async function scrollToBottom(force = false) {
  await nextTick();
  if (!force && !autoFollowMessages.value) return;
  const wrap = messageScroll.value?.wrapRef;
  messageScroll.value?.setScrollTop?.(wrap?.scrollHeight || 0);
}

function updateConversation(requestConversationId, conversation) {
  const index = conversations.value.findIndex((item) => item.id === requestConversationId);
  if (index >= 0 && conversation) conversations.value[index] = conversation;
}

function findAssistantMessage(turnId) {
  if (!turnId) return null;
  return messages.value.find((item) => item.role === 'assistant' && item.turn_id === turnId) || null;
}

function ensureToolCalls(message) {
  if (!Array.isArray(message.tool_calls)) message.tool_calls = [];
  return message.tool_calls;
}

function mergeToolCall(target, source, fallbackStatus) {
  if (!source?.call_id) return null;
  const calls = ensureToolCalls(target);
  const current = calls.find((item) => item.call_id === source.call_id);
  const next = { ...source };
  if (!next.status && fallbackStatus) next.status = fallbackStatus;
  if (current) {
    const expanded = current.expanded;
    const hasExpanded = Object.prototype.hasOwnProperty.call(current, 'expanded');
    Object.assign(current, next);
    if (hasExpanded) current.expanded = expanded;
    return current;
  }
  const created = { ...next, expanded: false };
  calls.push(created);
  return created;
}

function reconcileAssistantMessage(target, persisted) {
  if (!persisted || typeof persisted !== 'object') return target;
  const currentCalls = ensureToolCalls(target);
  const existingCalls = new Map(currentCalls.map((item) => [item.call_id, item]));
  const nextCalls = (Array.isArray(persisted.tool_calls) ? persisted.tool_calls : []).map((call) => {
    const current = existingCalls.get(call.call_id);
    if (!current) return { ...call, expanded: false };
    const expanded = current.expanded;
    const hasExpanded = Object.prototype.hasOwnProperty.call(current, 'expanded');
    Object.assign(current, call);
    if (hasExpanded) current.expanded = expanded;
    return current;
  });
  currentCalls.splice(0, currentCalls.length, ...nextCalls);
  const { tool_calls: _toolCalls, ...messageFields } = persisted;
  Object.assign(target, messageFields);
  target.tool_calls = currentCalls;
  return target;
}

function materializeAcceptedMessage(data) {
  const turnId = data?.turn_id;
  const persisted = data?.message;
  if (!turnId || !persisted || typeof persisted !== 'object') return null;
  let assistant = findAssistantMessage(turnId)
    || messages.value.find((item) => item.role === 'assistant' && item.id === persisted.id);
  if (assistant) {
    assistant.turn_id ||= turnId;
    reconcileAssistantMessage(assistant, { ...persisted, turn_id: turnId });
  } else {
    persisted.turn_id ||= turnId;
    persisted.status ||= 'streaming';
    ensureToolCalls(persisted);
    messages.value.push(persisted);
    assistant = findAssistantMessage(turnId);
  }
  activeTurnId.value = turnId;
  return assistant;
}

function reconcileTerminalEvent(requestConversationId, data, fallbackStatus) {
  const turnId = data?.turn_id;
  const assistant = findAssistantMessage(turnId);
  if (!assistant) return null;
  const persisted = data?.message;
  if (persisted && typeof persisted === 'object') {
    reconcileAssistantMessage(assistant, { ...persisted, turn_id: turnId, status: persisted.status || fallbackStatus });
  } else {
    assistant.status = fallbackStatus;
  }
  if (fallbackStatus === 'failed') {
    assistant.error = data?.error || data?.error_message || assistant.error || '生成失败，可重试';
  }
  updateConversation(requestConversationId, data?.conversation);
  if (activeTurnId.value === turnId) activeTurnId.value = null;
  return assistant;
}

function toolStatusText(status) {
  return {
    running: '调用中',
    succeeded: '完成',
    failed: '失败',
    awaiting_confirmation: '等待确认',
    cancelled: '已停止',
  }[status] || '等待中';
}

function formatToolPayload(value) {
  if (typeof value === 'string') return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function hasToolPayload(value) {
  return value !== undefined && value !== null;
}

function toggleToolDetails(tool) {
  tool.expanded = !tool.expanded;
}

function isWaitingForToolResult(message) {
  return message.status === 'streaming'
    && !String(message.content || '').trim()
    && Array.isArray(message.tool_calls)
    && message.tool_calls.length > 0;
}

async function decideQuotaConfirmation(message, decision) {
  const confirmation = message?.quota_confirmation;
  if (!confirmation || confirmation.deciding || confirmation.decided) return;
  confirmation.deciding = true;
  try {
    await aiApi.decideQuotaConfirmation(activeConversationId.value, confirmation.confirmation_id, decision);
    confirmation.decided = decision;
  } catch (error) {
    confirmation.error = error.message || '确认操作失败';
  } finally {
    confirmation.deciding = false;
  }
}

function applyEvent(requestConversationId, { event, data }) {
  // Ignore late chunks from a request whose conversation is no longer displayed.
  if (activeConversationId.value !== requestConversationId) return;
  if (event === 'user_message') {
    if (data.message && !messages.value.some((item) => item.id === data.message.id)) messages.value.push(data.message);
    updateConversation(requestConversationId, data.conversation);
  } else if (event === 'accepted') {
    if (!materializeAcceptedMessage(data)) return;
  } else if (event === 'delta') {
    const assistant = findAssistantMessage(data?.turn_id);
    if (!assistant) return;
    assistant.content = `${assistant.content || ''}${data.text || ''}`;
    assistant.status = 'streaming';
  } else if (event === 'status') {
    if (!findAssistantMessage(data?.turn_id)) return;
    streamStatus.value = data.status;
  } else if (event === 'tool_call_started') {
    const assistant = findAssistantMessage(data?.turn_id);
    if (!assistant || !mergeToolCall(assistant, data, 'running')) return;
  } else if (event === 'tool_call_finished') {
    const assistant = findAssistantMessage(data?.turn_id);
    if (!assistant || !mergeToolCall(assistant, data)) return;
  } else if (event === 'quota_confirmation_required') {
    const assistant = findAssistantMessage(data?.turn_id);
    if (!assistant) return;
    assistant.quota_confirmation = { ...data, deciding: false, decided: null, error: '' };
  } else if (event === 'completed') {
    if (!reconcileTerminalEvent(requestConversationId, data, 'succeeded')) return;
  } else if (event === 'cancelled') {
    if (!reconcileTerminalEvent(requestConversationId, data, 'cancelled')) return;
  } else if (event === 'error') {
    const assistant = reconcileTerminalEvent(requestConversationId, data, 'failed');
    if (!assistant) return;
    failedContent.value = activePrompt;
  }
  scrollToBottom();
}

async function send() {
  const prompt = content.value.trim();
  if (!prompt || streaming.value) return;
  let conversation = activeConversation.value;
  try {
    if (!conversation) conversation = await createConversation();
    if (!conversation) return;
    // Capture the target before awaiting the stream so later navigation cannot retarget events.
    const requestConversationId = conversation.id;
    content.value = '';
    failedContent.value = '';
    streaming.value = true;
    streamStatus.value = 'connecting';
    activeTurnId.value = null;
    activePrompt = prompt;
    abortController = new AbortController();
    await aiApi.streamMessage(requestConversationId, prompt, {
      signal: abortController.signal,
      onEvent: (event) => applyEvent(requestConversationId, event),
    });
  } catch (error) {
    const assistant = findAssistantMessage(activeTurnId.value);
    if (error.name === 'AbortError') {
      if (assistant && assistant.status === 'streaming') assistant.status = 'cancelled';
    } else {
      failedContent.value = prompt;
      if (assistant) {
        assistant.status = 'failed';
        assistant.error = error.message || '生成失败，可重试';
        scrollToBottom();
      } else {
        ElMessage.error(error.message || '生成失败，可重试');
      }
    }
  } finally {
    streaming.value = false;
    streamStatus.value = '';
    abortController = null;
  }
}

function stop() {
  const assistant = findAssistantMessage(activeTurnId.value);
  if (assistant && assistant.status === 'streaming') assistant.status = 'cancelled';
  abortController?.abort();
}

function retry() {
  content.value = failedContent.value;
  send();
}

function recoveryDescription(message) {
  return message?.recovery?.reason === 'tool_iteration_limit'
    ? '本轮工具查询已达到上限，回答已基于当前可用信息生成。'
    : '本轮工具参数多次无效，回答已保留当前可用信息。';
}

async function continueRecovery(message) {
  if (!message?.recovery || streaming.value) return;
  content.value = message.recovery.action === 'retry'
    ? '请重新查询并补全上一个问题。'
    : '我授权继续查询并补全上一个问题。';
  await send();
}

onMounted(loadInitial);
</script>

<template>
  <section class="ai-workspace">
    <aside class="conversation-panel">
      <div class="panel-heading">
        <strong>对话历史</strong>
        <ElButton
          class="conversation-create"
          plain
          size="small"
          aria-label="新建对话"
          @click="createConversation"><i class="i-ri-add-line"></i><span>新建</span></ElButton>
      </div>
      <ElScrollbar class="conversation-list">
        <button
          v-for="conversation in conversations"
          :key="conversation.id"
          class="conversation-item"
          :class="{ active: conversation.id === activeConversationId }"
          type="button"
          @click="openConversation(conversation.id)"
        >
          <span>{{ conversation.title }}</span>
          <ElPopconfirm
            title="删除这个对话？"
            @confirm="removeConversation(conversation.id)">
            <template #reference><i
              class="i-ri-delete-bin-line"
              @click.stop></i></template>
          </ElPopconfirm>
        </button>
      </ElScrollbar>
    </aside>

    <main class="chat-panel">
      <div class="chat-heading">
        <div>
          <strong>{{ activeConversation?.title || 'AI 助手' }}</strong>
        </div>
        <span
          v-if="streaming"
          class="live-status">{{ streamStatus === 'thinking' ? '正在分析' : '正在连接' }}</span>
      </div>

      <ElScrollbar
        ref="messageScroll"
        class="message-list"
        @scroll="handleMessageScroll">
        <ElEmpty
          v-if="messages.length === 0"
          description="输入问题开始对话" />
        <article
          v-for="message in messages"
          :key="message.id"
          class="message"
          :class="message.role">
          <div class="message-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
          <div
            v-if="message.role === 'assistant' && isWaitingForToolResult(message)"
            class="message-body tool-waiting">正在查询数据</div>
          <div
            v-else-if="message.role === 'assistant'"
            class="message-body markdown-body"
            v-html="renderAiMarkdown(message.content || '')"></div>
          <div
            v-else
            class="message-body">{{ message.content }}</div>
          <span
            v-if="message.role === 'assistant' && message.status === 'cancelled'"
            class="failed-label">已停止生成</span>
          <span
            v-else-if="message.role === 'assistant' && message.status === 'failed'"
            class="failed-label">{{ message.error || '生成失败，可重试' }}</span>
          <section
            v-if="message.role === 'assistant' && message.status === 'degraded' && message.recovery"
            class="message-recovery">
            <span>{{ recoveryDescription(message) }}</span>
            <button
              class="message-recovery__action"
              type="button"
              :aria-label="message.recovery.label"
              :disabled="streaming"
              @click="continueRecovery(message)">{{ message.recovery.label }}</button>
          </section>
          <section
            v-if="message.role === 'assistant' && message.quota_confirmation"
            class="quota-confirmation">
            <strong>配额调整确认</strong>
            <p>{{ message.quota_confirmation.preview.resource }}：{{ message.quota_confirmation.preview.old_hard_limit }} → {{ message.quota_confirmation.preview.new_hard_limit }} {{ message.quota_confirmation.preview.unit }}</p>
            <p v-if="message.quota_confirmation.preview.change_reason">理由：{{ message.quota_confirmation.preview.change_reason }}</p>
            <p
              v-if="message.quota_confirmation.error"
              class="failed-label">{{ message.quota_confirmation.error }}</p>
            <div class="quota-confirmation__actions">
              <ElButton
                size="small"
                :disabled="message.quota_confirmation.deciding || message.quota_confirmation.decided"
                @click="decideQuotaConfirmation(message, 'cancel')">取消</ElButton>
              <ElButton
                size="small"
                type="danger"
                :loading="message.quota_confirmation.deciding"
                :disabled="message.quota_confirmation.deciding || message.quota_confirmation.decided"
                @click="decideQuotaConfirmation(message, 'confirm')">确认执行</ElButton>
            </div>
          </section>
          <section
            v-if="message.role === 'assistant' && message.tool_calls?.length"
            class="tool-trace"
            aria-label="工具调用">
            <span class="tool-trace__title">工具调用</span>
            <div
              v-for="tool in message.tool_calls"
              :key="tool.call_id"
              class="tool-trace__item">
              <button
                class="tool-trace__summary"
                type="button"
                :aria-expanded="Boolean(tool.expanded)"
                @click="toggleToolDetails(tool)">
                <span class="tool-trace__name">{{ tool.tool_name }}</span>
                <span
                  class="tool-trace__status"
                  :class="`is-${tool.status}`">{{ toolStatusText(tool.status) }}</span>
                <span
                  v-if="tool.elapsed_ms !== undefined"
                  class="tool-trace__elapsed">{{ tool.elapsed_ms }} ms</span>
                <span
                  v-if="tool.truncated"
                  class="tool-trace__truncated">结果已截断</span>
                <i :class="tool.expanded ? 'i-ri-arrow-up-s-line' : 'i-ri-arrow-down-s-line'"></i>
              </button>
              <div
                v-if="tool.expanded"
                class="tool-trace__details">
                <div v-if="hasToolPayload(tool.arguments)">
                  <strong>参数</strong>
                  <pre>{{ formatToolPayload(tool.arguments) }}</pre>
                </div>
                <div v-if="hasToolPayload(tool.result)">
                  <strong>返回内容</strong>
                  <pre>{{ formatToolPayload(tool.result) }}</pre>
                </div>
              </div>
            </div>
          </section>
        </article>
      </ElScrollbar>

      <div class="composer">
        <p class="composer__notice">AI 可能会出错，请核查重要信息。</p>
        <div class="composer__field">
          <ElInput
            v-model="content"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            maxlength="32000"
            placeholder="询问容量、告警、项目或存储趋势…"
            @keydown.ctrl.enter.prevent="send"
          />
          <span class="composer__shortcut">Ctrl + Enter</span>
          <ElSelect
            v-model="selectedModelId"
            class="composer__model"
            aria-label="选择模型"
            placeholder="选择模型"
            :disabled="streaming">
            <ElOption
              v-for="model in models"
              :key="model.id"
              :label="model.name"
              :value="model.id" />
          </ElSelect>
          <ElButton
            v-if="failedContent && !streaming"
            class="composer__retry"
            circle
            aria-label="重试生成"
            @click="retry"><i class="i-ri-refresh-line"></i></ElButton>
          <ElButton
            v-else-if="streaming"
            class="composer__send composer__send--stop"
            circle
            aria-label="停止生成"
            @click="stop"><i class="i-ri-stop-fill"></i></ElButton>
          <ElButton
            v-else
            class="composer__send"
            circle
            aria-label="发送消息"
            :disabled="!content.trim()"
            @click="send"><i class="i-ri-arrow-up-line"></i></ElButton>
        </div>
      </div>
    </main>
  </section>
</template>

<style scoped lang="scss">
.ai-workspace { display: grid; flex: 1 1 0; grid-template-columns: 248px minmax(0, 1fr); min-height: 0; height: 100%; max-height: 100%; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); overflow: hidden; }
.conversation-panel { display: flex; flex-direction: column; min-width: 0; padding: 16px 12px; border-right: 1px solid var(--border-color); background: var(--bg-secondary); }
.panel-heading, .chat-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.panel-heading { margin-bottom: 12px; }
.conversation-create { color: var(--primary-color); border-color: var(--el-color-primary-light-5); background: var(--el-color-primary-light-9); }
.conversation-create:hover, .conversation-create:focus-visible { color: var(--primary-color); border-color: var(--primary-color); background: var(--el-color-primary-light-8); }
.conversation-create i { margin-right: 4px; font-size: 14px; }
.conversation-list { flex: 1; }
.conversation-item { width: 100%; border: 0; background: transparent; display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px; margin-bottom: 4px; border-radius: 8px; color: var(--text-secondary); cursor: pointer; text-align: left; }
.conversation-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conversation-item:hover, .conversation-item.active { color: var(--primary-color); background: var(--bg-hover); }
.chat-panel { display: flex; min-width: 0; min-height: 0; flex-direction: column; overflow: hidden; }
.chat-heading { flex: none; min-height: 56px; padding: 0 22px; }
.live-status { color: var(--primary-color); font-size: 13px; }
.message-list { flex: 1; min-height: 0; padding: 20px 0; }
.message { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 12px; max-width: 920px; margin: 0 auto 18px; padding: 0 24px; }
.message-role { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; background: var(--el-color-primary-light-9); color: var(--primary-color); font-size: 12px; font-weight: 600; }
.message.user .message-body { background: var(--bg-secondary); border-radius: 10px; padding: 10px 13px; white-space: pre-wrap; }
.message-body { min-width: 0; line-height: 1.75; color: var(--text-primary); }
.tool-waiting { color: var(--text-secondary); font-size: 13px; }
.failed-label { grid-column: 2; color: var(--el-color-danger); font-size: 12px; }
.message-recovery { grid-column: 2; display: flex; align-items: center; flex-wrap: wrap; gap: 8px; color: var(--el-color-warning); font-size: 12px; }
.message-recovery__action { padding: 4px 9px; border: 1px solid var(--el-color-warning-light-3); border-radius: var(--radius-full); color: var(--el-color-warning); background: var(--el-color-warning-light-9); cursor: pointer; font: inherit; }
.message-recovery__action:hover:not(:disabled), .message-recovery__action:focus-visible { border-color: var(--el-color-warning); outline: none; }
.message-recovery__action:disabled { cursor: not-allowed; opacity: .65; }
.quota-confirmation { grid-column: 2; display: grid; gap: 6px; padding: var(--spacing-sm); border: 1px solid var(--el-color-warning-light-5); border-radius: var(--radius-sm); background: var(--el-color-warning-light-9); color: var(--text-primary); font-size: 12px; }
.quota-confirmation p { margin: 0; }
.quota-confirmation__actions { display: flex; gap: var(--spacing-sm); }
.tool-trace { grid-column: 2; display: grid; gap: 6px; margin-top: -8px; color: var(--text-secondary); font-size: 12px; }
.tool-trace__title { color: var(--text-tertiary); font-weight: 600; }
.tool-trace__item { border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-secondary); overflow: hidden; }
.tool-trace__summary { width: 100%; display: flex; align-items: center; gap: 8px; padding: 7px 10px; color: inherit; background: transparent; cursor: pointer; text-align: left; }
.tool-trace__summary:focus-visible { outline: 2px solid var(--primary-color); outline-offset: -2px; }
.tool-trace__name { color: var(--text-primary); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-weight: 600; }
.tool-trace__status { color: var(--text-secondary); }
.tool-trace__status.is-succeeded { color: var(--el-color-success); }
.tool-trace__status.is-failed { color: var(--el-color-danger); }
.tool-trace__status.is-running { color: var(--primary-color); }
.tool-trace__elapsed, .tool-trace__truncated { color: var(--text-tertiary); }
.tool-trace__summary i { margin-left: auto; }
.tool-trace__details { display: grid; gap: 8px; padding: 0 10px 10px; border-top: 1px solid var(--border-color); }
.tool-trace__details > div { display: grid; gap: 4px; }
.tool-trace__details strong { margin-top: 8px; color: var(--text-secondary); font-size: 12px; }
.tool-trace__details pre { max-height: 220px; margin: 0; overflow: auto; padding: 8px; border-radius: var(--radius-sm); background: var(--bg-primary); color: var(--text-primary); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
.composer { flex: none; padding: 10px 20px 18px; background: var(--bg-primary); }
.composer__notice { margin: 0 0 8px; color: var(--text-tertiary); font-size: 12px; text-align: center; }
.composer__field { position: relative; max-width: 920px; margin: 0 auto; }
.composer__field :deep(.el-textarea__inner) { min-height: 74px !important; padding: 13px 210px 28px 16px; border: 1px solid var(--text-tertiary); border-radius: 18px; box-shadow: var(--shadow-sm); resize: none; }
.composer__field :deep(.el-textarea__inner:focus) { box-shadow: 0 0 0 2px var(--el-color-primary-light-7); }
.composer__shortcut { position: absolute; bottom: 12px; left: 16px; color: var(--text-tertiary); font-size: 12px; pointer-events: none; }
.composer__model { position: absolute; right: 56px; bottom: 10px; width: 132px; }
.composer__model :deep(.el-select__wrapper) { min-height: 36px; border-radius: var(--radius-full); background: var(--bg-secondary); box-shadow: none; }
.composer__send, .composer__retry { position: absolute; right: 10px; bottom: 10px; width: 36px; height: 36px; padding: 0; border: 0; color: #fff; background: var(--text-primary); box-shadow: none; }
.composer__send:hover, .composer__retry:hover { color: #fff; background: var(--text-secondary); }
.composer__send:disabled { color: var(--text-disabled); background: var(--bg-tertiary); }
.composer__send--stop { background: var(--el-color-danger); }
.composer__send--stop:hover { background: var(--el-color-danger); }
.composer__retry { right: 54px; color: var(--text-secondary); background: var(--bg-secondary); border: 1px solid var(--border-color); }
.composer__retry:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.markdown-body :deep(pre) { overflow: auto; padding: 12px; border-radius: 8px; background: #18212f; color: #e8eef7; }
.markdown-body :deep(code) { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.markdown-body :deep(a) { color: var(--primary-color); }
@media (max-width: 860px) { .ai-workspace { grid-template-columns: 1fr; } .conversation-panel { max-height: 220px; border-right: 0; border-bottom: 1px solid var(--border-color); } .chat-panel { min-height: 620px; } }
</style>
