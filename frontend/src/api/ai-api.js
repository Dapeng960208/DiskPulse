import { getToken } from '@/utils/authorization';

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

export async function streamConversationMessage(conversationId, content, { signal, onEvent }) {
  // Native fetch exposes the response body stream; the shared Axios wrapper buffers browser responses.
  const response = await fetch(apiUrl(`/ai/conversations/${conversationId}/messages/stream`), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${getToken()}`,
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ content }),
    signal,
  });
  if (!response.ok) await responseError(response);
  if (!response.body) throw new Error('浏览器不支持流式响应');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    // Transport chunks can split one SSE event, so retain the trailing incomplete block.
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || '';
    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (parsed) onEvent(parsed);
    }
    if (done) break;
  }
  const parsed = parseSseBlock(buffer.trim());
  if (parsed) onEvent(parsed);
}

export default {
  listModels: () => request('get', '/ai/models'),
  listConversations: () => request('get', '/ai/conversations'),
  createConversation: (payload) => request('post', '/ai/conversations', { data: payload }),
  getConversation: (id) => request('get', `/ai/conversations/${id}`),
  deleteConversation: (id) => request('delete', `/ai/conversations/${id}`),
  streamMessage: streamConversationMessage,
  listAdminModels: () => request('get', '/admin/ai-models'),
  createModel: (payload) => request('post', '/admin/ai-models', { data: payload }),
  updateModel: (id, payload) => request('patch', `/admin/ai-models/${id}`, { data: payload }),
  deleteModel: (id) => request('delete', `/admin/ai-models/${id}`),
  testModel: (id) => request('post', `/admin/ai-models/${id}/test`),
  listAudits: (params) => request('get', '/admin/ai-audits', { params }),
  getAudit: (id) => request('get', `/admin/ai-audits/${id}`),
  getConversationAudits: (id) => request('get', `/admin/ai-audits/conversations/${id}`),
};
