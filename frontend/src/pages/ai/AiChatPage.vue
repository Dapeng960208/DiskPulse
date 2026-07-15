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
const toolStatus = ref([]);
const messageScroll = ref();
let abortController = null;

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
  toolStatus.value = [];
  return conversation;
}

async function openConversation(id) {
  if (streaming.value) return;
  const conversation = await aiApi.getConversation(id);
  activeConversationId.value = id;
  selectedModelId.value = conversation.model_id;
  messages.value = conversation.messages || [];
  toolStatus.value = [];
  await scrollToBottom();
}

async function removeConversation(id) {
  await aiApi.deleteConversation(id);
  conversations.value = conversations.value.filter((item) => item.id !== id);
  if (activeConversationId.value === id) {
    activeConversationId.value = null;
    messages.value = [];
  }
}

async function scrollToBottom() {
  await nextTick();
  messageScroll.value?.setScrollTop?.(messageScroll.value.wrapRef?.scrollHeight || 0);
}

function applyEvent(requestConversationId, { event, data }) {
  if (activeConversationId.value !== requestConversationId) return;
  if (event === 'user_message') {
    messages.value.push(data.message);
    const index = conversations.value.findIndex((item) => item.id === requestConversationId);
    if (index >= 0) conversations.value[index] = data.conversation;
  } else if (event === 'delta') {
    let assistant = messages.value.at(-1);
    if (!assistant || assistant.role !== 'assistant' || !assistant.streaming) {
      assistant = { id: `stream-${Date.now()}`, role: 'assistant', content: '', streaming: true };
      messages.value.push(assistant);
    }
    assistant.content += data.text;
  } else if (event === 'status') {
    streamStatus.value = data.status;
  } else if (event === 'tool_call_started') {
    toolStatus.value.push({ ...data, status: 'running' });
  } else if (event === 'tool_call_finished') {
    const item = [...toolStatus.value].reverse().find((entry) => entry.tool_name === data.tool_name && entry.status === 'running');
    if (item) item.status = data.status;
  } else if (event === 'completed') {
    const index = messages.value.findIndex((item) => item.streaming);
    if (index >= 0) messages.value[index] = data.message;
    else messages.value.push(data.message);
    const conversationIndex = conversations.value.findIndex((item) => item.id === requestConversationId);
    if (conversationIndex >= 0) conversations.value[conversationIndex] = data.conversation;
  } else if (event === 'error') {
    throw new Error(data.message || '生成失败');
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
    const requestConversationId = conversation.id;
    content.value = '';
    failedContent.value = '';
    streaming.value = true;
    streamStatus.value = 'connecting';
    toolStatus.value = [];
    abortController = new AbortController();
    await aiApi.streamMessage(requestConversationId, prompt, {
      signal: abortController.signal,
      onEvent: (event) => applyEvent(requestConversationId, event),
    });
  } catch (error) {
    if (error.name !== 'AbortError') {
      failedContent.value = prompt;
      ElMessage.error(error.message || '生成失败，可重试');
      const pending = messages.value.find((item) => item.streaming);
      if (pending) pending.failed = true;
    }
  } finally {
    streaming.value = false;
    streamStatus.value = '';
    abortController = null;
  }
}

function stop() {
  abortController?.abort();
}

function retry() {
  content.value = failedContent.value;
  send();
}

onMounted(loadInitial);
</script>

<template>
  <section class="ai-workspace">
    <aside class="conversation-panel">
      <div class="panel-heading">
        <strong>对话</strong>
        <ElButton
          plain
          size="small"
          @click="createConversation">新建</ElButton>
      </div>
      <ElSelect
        v-model="selectedModelId"
        class="model-select"
        placeholder="选择模型"
        :disabled="streaming">
        <ElOption
          v-for="model in models"
          :key="model.id"
          :label="model.name"
          :value="model.id" />
      </ElSelect>
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
          <small>查询 DiskPulse 中你有权访问的只读数据</small>
        </div>
        <span
          v-if="streaming"
          class="live-status">{{ streamStatus === 'thinking' ? '正在分析' : '正在连接' }}</span>
      </div>

      <ElScrollbar
        ref="messageScroll"
        class="message-list">
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
            v-if="message.role === 'assistant'"
            class="message-body markdown-body"
            v-html="renderAiMarkdown(message.content)"></div>
          <div
            v-else
            class="message-body">{{ message.content }}</div>
          <span
            v-if="message.failed"
            class="failed-label">生成中断</span>
        </article>
        <div
          v-if="toolStatus.length"
          class="tool-log">
          <div
            v-for="(tool, index) in toolStatus"
            :key="`${tool.tool_name}-${index}`">
            <i :class="tool.status === 'running' ? 'i-ri-loader-4-line animate-spin' : 'i-ri-check-line'"></i>
            {{ tool.tool_name }} · {{ tool.status === 'running' ? '查询中' : tool.status === 'succeeded' ? '完成' : '失败' }}
          </div>
        </div>
      </ElScrollbar>

      <div class="composer">
        <ElInput
          v-model="content"
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 6 }"
          maxlength="32000"
          placeholder="询问容量、告警、项目或存储趋势…"
          @keydown.ctrl.enter.prevent="send"
        />
        <div class="composer-actions">
          <span>Ctrl + Enter 发送</span>
          <ElButton
            v-if="failedContent && !streaming"
            plain
            @click="retry">重试</ElButton>
          <ElButton
            v-if="streaming"
            type="danger"
            plain
            @click="stop">停止生成</ElButton>
          <ElButton
            v-else
            type="primary"
            :disabled="!content.trim()"
            @click="send">发送</ElButton>
        </div>
      </div>
    </main>
  </section>
</template>

<style scoped lang="scss">
.ai-workspace { display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 680px; height: calc(100vh - 180px); background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); overflow: hidden; }
.conversation-panel { display: flex; flex-direction: column; min-width: 0; padding: 16px 12px; border-right: 1px solid var(--border-color); background: var(--bg-secondary); }
.panel-heading, .chat-heading, .composer-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.panel-heading { margin-bottom: 12px; }
.model-select { width: 100%; margin-bottom: 12px; }
.conversation-list { flex: 1; }
.conversation-item { width: 100%; border: 0; background: transparent; display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px; margin-bottom: 4px; border-radius: 8px; color: var(--text-secondary); cursor: pointer; text-align: left; }
.conversation-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.conversation-item:hover, .conversation-item.active { color: var(--primary-color); background: var(--bg-hover); }
.chat-panel { display: flex; min-width: 0; flex-direction: column; }
.chat-heading { min-height: 64px; padding: 0 22px; border-bottom: 1px solid var(--border-color); }
.chat-heading small { display: block; margin-top: 3px; color: var(--text-tertiary); }
.live-status { color: var(--primary-color); font-size: 13px; }
.message-list { flex: 1; padding: 20px 0; }
.message { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 12px; max-width: 920px; margin: 0 auto 18px; padding: 0 24px; }
.message-role { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; background: var(--el-color-primary-light-9); color: var(--primary-color); font-size: 12px; font-weight: 600; }
.message.user .message-body { background: var(--bg-secondary); border-radius: 10px; padding: 10px 13px; white-space: pre-wrap; }
.message-body { min-width: 0; line-height: 1.75; color: var(--text-primary); }
.failed-label { grid-column: 2; color: var(--el-color-danger); font-size: 12px; }
.tool-log { max-width: 872px; margin: -6px auto 18px; padding: 10px 14px; border-left: 3px solid var(--el-color-primary-light-5); color: var(--text-secondary); font-size: 12px; line-height: 1.8; }
.composer { padding: 14px 20px 18px; border-top: 1px solid var(--border-color); }
.composer-actions { margin-top: 10px; }
.composer-actions span { color: var(--text-tertiary); font-size: 12px; margin-right: auto; }
.markdown-body :deep(pre) { overflow: auto; padding: 12px; border-radius: 8px; background: #18212f; color: #e8eef7; }
.markdown-body :deep(code) { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }
.markdown-body :deep(a) { color: var(--primary-color); }
@media (max-width: 860px) { .ai-workspace { grid-template-columns: 1fr; height: auto; } .conversation-panel { max-height: 220px; border-right: 0; border-bottom: 1px solid var(--border-color); } .chat-panel { min-height: 620px; } }
</style>
