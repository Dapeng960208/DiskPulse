import { getToken } from '@/utils/authorization';
import { mockEnabled, mockGateway } from '@/mocks/runtime';

const KNOWN_SSE_EVENTS = new Set([
  'accepted',
  'user_message',
  'status',
  'delta',
  'tool_call_started',
  'tool_call_finished',
  'quota_confirmation_required',
  'completed',
  'error',
  'cancelled',
]);
const TERMINAL_SSE_EVENTS = new Set(['completed', 'error', 'cancelled']);

async function request(method, url, { data, params } = {}) {
  // Lazy loading breaks the router/request initialization cycle while preserving the shared client.
  const { default: baseRequest } = await import('./support/base-request');
  const response = method === 'get' || method === 'delete'
    ? await baseRequest[method](url, { params })
    : await baseRequest[method](url, data, { params });
  return response.data;
}

export function parseSseBlock(block) {
  let event = 'message';
  const data = [];
  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return null;
  const raw = data.join('\n');
  try {
    return { event, data: JSON.parse(raw) };
  } catch {
    return { event, data: raw };
  }
}

function dispatchSseEvent(parsed, state, onEvent) {
  if (KNOWN_SSE_EVENTS.has(parsed.event)) {
    if (!isValidSsePayload(parsed.event, parsed.data)) {
      throw new Error('AI 流式事件数据无效');
    }
    if (state.terminal) {
      throw new Error('AI 流式响应已结束，不能接收后续事件');
    }
    if (parsed.event === 'accepted') state.accepted = true;
    if (TERMINAL_SSE_EVENTS.has(parsed.event)) {
      if (!state.accepted) throw new Error('AI 流式响应在确认前结束');
      state.terminal = true;
    }
  }
  onEvent(parsed);
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function hasTurnId(data) {
  return typeof data.turn_id === 'string' || typeof data.turn_id === 'number';
}

function isValidSsePayload(event, data) {
  if (!isObject(data)) return false;
  if (event === 'user_message') return hasTurnId(data) && isObject(data.message) && isObject(data.conversation);
  if (event === 'accepted') return hasTurnId(data) && isObject(data.message);
  if (event === 'status') return hasTurnId(data) && typeof data.status === 'string';
  if (event === 'delta') return hasTurnId(data) && typeof data.text === 'string';
  if (event === 'tool_call_started' || event === 'tool_call_finished') {
    return hasTurnId(data) && typeof data.call_id === 'string';
  }
  if (event === 'quota_confirmation_required') return hasTurnId(data) && typeof data.confirmation_id === 'string' && isObject(data.preview);
  if (TERMINAL_SSE_EVENTS.has(event)) return hasTurnId(data) && isObject(data.message);
  return true;
}

function apiUrl(path) {
  return `${String(import.meta.env.VITE_APP_API_BASE_URL || '').replace(/\/$/, '')}${path}`;
}

async function responseError(response) {
  let message = `请求失败 (${response.status})`;
  try {
    const body = await response.json();
    message = body.detail || body.message || message;
  } catch {
    // Keep the status-based fallback for non-JSON responses.
  }
  const error = new Error(message);
  error.status = response.status;
  throw error;
}

export async function streamConversationMessage(conversationId, content, {
  signal,
  onEvent,
  reasoning = 'auto',
}) {
  if (mockEnabled()) {
    const events = await mockGateway().streamAiMessage(
      getToken(),
      conversationId,
      content,
      { reasoning },
    );
    const state = { accepted: false, terminal: false };
    for (const parsed of events) {
      if (signal?.aborted) throw new DOMException('请求已取消', 'AbortError');
      dispatchSseEvent(parsed, state, onEvent);
    }
    return;
  }
  // Native fetch exposes the response body stream; the shared Axios wrapper buffers browser responses.
  const response = await fetch(apiUrl(`/ai/conversations/${conversationId}/messages/stream`), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ content, reasoning }),
    signal,
  });
  if (!response.ok) await responseError(response);
  if (!response.body) throw new Error('浏览器不支持流式响应');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const state = { accepted: false, terminal: false };
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    // Transport chunks can split one SSE event, so retain the trailing incomplete block.
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (parsed) dispatchSseEvent(parsed, state, onEvent);
    }
    if (done) break;
  }
  const parsed = parseSseBlock(buffer.trim());
  if (parsed) dispatchSseEvent(parsed, state, onEvent);
  if (!state.accepted) throw new Error('AI 流式响应未收到确认事件');
  if (!state.terminal) throw new Error('AI 流式响应未正常结束');
}

export default {
  listModels: () => request('get', '/ai/models'),
  listConversations: () => request('get', '/ai/conversations'),
  createConversation: (payload) => request('post', '/ai/conversations', { data: payload }),
  getConversation: (id) => request('get', `/ai/conversations/${id}`),
  deleteConversation: (id) => request('delete', `/ai/conversations/${id}`),
  decideQuotaConfirmation: (conversationId, confirmationId, decision) => request(
    'post',
    `/ai/conversations/${conversationId}/quota-confirmations/${confirmationId}`,
    { data: { decision } },
  ),
  streamMessage: streamConversationMessage,
  listAdminModels: () => request('get', '/admin/ai-models'),
  createModel: (payload) => request('post', '/admin/ai-models', { data: payload }),
  updateModel: (id, payload) => request('patch', `/admin/ai-models/${id}`, { data: payload }),
  deleteModel: (id) => request('delete', `/admin/ai-models/${id}`),
  testModel: (id) => request('post', `/admin/ai-models/${id}/test`),
  refreshModelCapabilities: (id) => request(
    'post',
    `/admin/ai-models/${id}/capabilities/refresh`,
  ),
  getAiSettings: () => request('get', '/admin/ai-settings'),
  updateAiSettings: (payload) => request('patch', '/admin/ai-settings', { data: payload }),
  listAudits: (params) => request('get', '/admin/ai-audits', { params }),
  getAudit: (id) => request('get', `/admin/ai-audits/${id}`),
  getConversationAudits: (id) => request('get', `/admin/ai-audits/conversations/${id}`),
};
