import DOMPurify from 'dompurify';
import MarkdownIt from 'markdown-it';

const markdown = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
});

const defaultLinkOpen = markdown.renderer.rules.link_open
  || ((tokens, index, options, env, self) => self.renderToken(tokens, index, options));

markdown.renderer.rules.link_open = (tokens, index, options, env, self) => {
  const href = tokens[index].attrGet('href') || '';
  if (!/^(https?:|mailto:|\/)/i.test(href)) tokens[index].attrSet('href', '#');
  tokens[index].attrSet('target', '_blank');
  tokens[index].attrSet('rel', 'noopener noreferrer');
  return defaultLinkOpen(tokens, index, options, env, self);
};

export function renderAiMarkdown(source) {
  const safeSource = String(source || '').replace(/\b(?:javascript|vbscript|data):/gi, '');
  return DOMPurify.sanitize(markdown.render(safeSource), {
    USE_PROFILES: { html: true },
  });
}
