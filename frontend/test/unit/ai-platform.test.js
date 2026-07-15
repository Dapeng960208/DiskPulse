import { describe, expect, it } from 'vitest';
import routes from '@/router/routes';
import { parseSseBlock } from '@/api/ai-api';
import { renderAiMarkdown } from '@/services/ai-markdown';


describe('AI platform contracts', () => {
  it('exposes AI chat to authenticated users and AI center to super admins', () => {
    const chat = routes
      .flatMap((route) => route.children || [])
      .find((route) => route.path === 'ai/chat');
    const admin = routes.find((route) => route.path === '/admin');
    const center = admin.children.find((route) => route.path === 'ai-center');

    expect(chat.meta.title).toBe('AI 助手');
    expect(chat.meta.isRoot).toBe(true);
    expect(center.meta.title).toBe('AI 中心');
    expect(center.meta.isAccessible()).toBe(403);
  });

  it('parses multi-line SSE data blocks', () => {
    expect(parseSseBlock('event: delta\ndata: {"text":"容量"}')).toEqual({
      event: 'delta',
      data: { text: '容量' },
    });
  });

  it('sanitizes HTML and unsafe links in assistant markdown', () => {
    const html = renderAiMarkdown('[安全](https://example.com) [危险](javascript:alert(1)) <script>alert(1)</script>');

    expect(html).toContain('https://example.com');
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('<script>');
  });
});
