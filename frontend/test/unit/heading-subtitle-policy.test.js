import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

function vueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return vueFiles(path);
    return entry.name.endsWith('.vue') ? [path] : [];
  });
}

const headingSubtitlePattern = /<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>(?:\s*<\/[A-Za-z][^>]*>)*\s*<p[^>]*class=["'][^"']*(?:subtitle|description|hint)[^"']*["']/i;

describe('heading and subtitle policy', () => {
  it('does not render a descriptive subtitle immediately after a heading', () => {
    const offenders = vueFiles(resolve(process.cwd(), 'src'))
      .filter((path) => headingSubtitlePattern.test(readFileSync(path, 'utf8')))
      .map((path) => path.replace(`${resolve(process.cwd(), 'src')}\\`, 'src/'));

    expect(offenders).toEqual([]);
  });

  it('records the site-wide prohibition in the frontend standard', () => {
    const standard = readFileSync(resolve(process.cwd(), '../docs/standards/frontend/frontend-design-standard.md'), 'utf8');

    expect(standard).toContain('禁止在标题后设置描述性副标题');
  });
});
