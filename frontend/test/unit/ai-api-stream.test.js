import { beforeEach, describe, expect, it, vi } from 'vitest';

const request = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock('@/api/support/base-request', () => ({ default: request }));
vi.mock('@/utils/authorization', () => ({ getToken: () => 'test-token' }));

const { default: aiApi, streamConversationMessage } = await import('@/api/ai-api');

function streamResponse(chunks) {
  let index = 0;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: vi.fn(async () => {
          if (index >= chunks.length) return { done: true };
          return { done: false, value: new TextEncoder().encode(chunks[index++]) };
        }),
      }),
    },
  };
}

describe('AI API and SSE stream', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    request.get.mockResolvedValue({ data: [] });
    request.post.mockResolvedValue({ data: {} });
    request.patch.mockResolvedValue({ data: {} });
    request.delete.mockResolvedValue({ data: {} });
  });

  it('dispatches every AI REST operation through the authenticated request', async () => {
    await aiApi.listModels();
    await aiApi.listConversations();
    await aiApi.createConversation({ model_id: 1 });
    await aiApi.getConversation(3);
    await aiApi.deleteConversation(3);
    await aiApi.listAdminModels();
    await aiApi.createModel({ name: 'model' });
    await aiApi.updateModel(4, { enabled: true });
    await aiApi.deleteModel(4);
    await aiApi.testModel(4);
    await aiApi.listAudits({ page: 2 });
    await aiApi.getAudit(5);
    await aiApi.getConversationAudits(3);

    expect(request.get).toHaveBeenCalledWith('/ai/models', { params: undefined });
    expect(request.post).toHaveBeenCalledWith('/ai/conversations', { model_id: 1 }, { params: undefined });
    expect(request.patch).toHaveBeenCalledWith('/admin/ai-models/4', { enabled: true }, { params: undefined });
    expect(request.get).toHaveBeenCalledWith('/admin/ai-audits', { params: { page: 2 } });
  });

  it('parses events split across response chunks and flushes the final block', async () => {
    global.fetch = vi.fn().mockResolvedValue(streamResponse([
      'event: accepted\ndata: {"id":1}\n\nevent: del',
      'ta\ndata: {"text":"容量"}\n\nevent: completed\ndata: {"ok":true}',
    ]));
    const events = [];

    await streamConversationMessage(8, 'question', { onEvent: (event) => events.push(event) });

    expect(events).toEqual([
      { event: 'accepted', data: { id: 1 } },
      { event: 'delta', data: { text: '容量' } },
      { event: 'completed', data: { ok: true } },
    ]);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-token');
  });

  it.each([
    [
      'the missing accepted event',
      ['event: delta\ndata: {"turn_id":"turn-missing-accepted","text":"部分回答"}\n\nevent: completed\ndata: {"turn_id":"turn-missing-accepted","message":{}}'],
    ],
    [
      'the missing terminal event',
      ['event: accepted\ndata: {"turn_id":"turn-missing-terminal","message":{"id":1,"role":"assistant"}}\n\nevent: delta\ndata: {"turn_id":"turn-missing-terminal","text":"部分回答"}'],
    ],
    [
      'invalid data for a known event',
      ['event: accepted\ndata: {"turn_id":"turn-invalid-data","message":{"id":2,"role":"assistant"}}\n\nevent: delta\ndata: not-json\n\nevent: completed\ndata: {"turn_id":"turn-invalid-data","message":{"id":2,"role":"assistant"}}'],
    ],
  ])('rejects an SSE stream with %s', async (_description, chunks) => {
    global.fetch = vi.fn().mockResolvedValue(streamResponse(chunks));

    await expect(streamConversationMessage(8, 'question', { onEvent: vi.fn() })).rejects.toThrow();
  });

  it('surfaces JSON HTTP errors and missing stream support', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: async () => ({ detail: '请求过于频繁' }),
    });
    await expect(streamConversationMessage(1, 'q', { onEvent: vi.fn() })).rejects.toMatchObject({
      message: '请求过于频繁',
      status: 429,
    });

    global.fetch = vi.fn().mockResolvedValue({ ok: true, body: null });
    await expect(streamConversationMessage(1, 'q', { onEvent: vi.fn() })).rejects.toThrow('不支持流式响应');
  });
});
