import { describe, expect, it } from 'vitest';
import {
  DEMO_PASSWORD,
  createMockGateway,
} from '@/mocks/runtime.js';

describe('AI reasoning mock runtime contract', () => {
  it('exposes model reasoning capabilities and one administrator default model', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const models = await gateway.request('get', '/ai/models', undefined, superadmin.token);

    expect(models.filter((item) => item.is_default)).toHaveLength(1);
    expect(models).toEqual(expect.arrayContaining([
      expect.objectContaining({
        reasoning_control: expect.objectContaining({
          kind: expect.stringMatching(/^(effort|toggle|none)$/),
          options: expect.any(Array),
          source: expect.stringMatching(/^(provider|official_catalog|unknown)$/),
          status: expect.any(String),
        }),
      }),
    ]));
  });

  it('supports default-model settings, capability refresh, and default conversation creation', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    expect(await gateway.request('get', '/admin/ai-settings', undefined, superadmin.token))
      .toEqual({ default_chat_model_id: 1 });

    expect(await gateway.request(
      'patch',
      '/admin/ai-settings',
      { default_chat_model_id: 3 },
      superadmin.token,
    )).toEqual({ default_chat_model_id: 3 });

    const refreshed = await gateway.request(
      'post',
      '/admin/ai-models/3/capabilities/refresh',
      undefined,
      superadmin.token,
    );
    expect(refreshed).toEqual(expect.objectContaining({
      id: 3,
      capability_status: 'ready',
      capability_source: expect.stringMatching(/^(provider|official_catalog)$/),
    }));

    const conversation = await gateway.request(
      'post',
      '/ai/conversations',
      { title: '使用默认模型' },
      superadmin.token,
    );
    expect(conversation.model_id).toBe(3);
  });

  it('preserves the selected reasoning value in mock streaming user messages', async () => {
    const gateway = createMockGateway();
    const superadmin = await gateway.login('demo-superadmin', DEMO_PASSWORD);

    const events = await gateway.streamAiMessage(
      superadmin.token,
      1,
      '请深度分析',
      { reasoning: 'high' },
    );

    expect(events).toEqual(expect.arrayContaining([
      expect.objectContaining({
        event: 'user_message',
        data: expect.objectContaining({
          message: expect.objectContaining({
            role: 'user',
            content: '请深度分析',
            reasoning: 'high',
          }),
        }),
      }),
    ]));
  });
});
