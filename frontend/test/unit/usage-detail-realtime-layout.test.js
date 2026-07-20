import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('user-directory realtime trend layout', () => {
  it('constrains the capacity trend to the detail content pane instead of extending into the footer', () => {
    const page = source('src/pages/usage/UsageDetailPage.vue');

    expect(page).toContain('class="usage-detail-page__tabs"');
    expect(page).toContain('class="usage-detail-page__capacity-tab"');
    expect(page).toContain('class="usage-detail-page__realtime-content"');
    expect(page).toContain(':fill-content="true"');
    expect(page).toMatch(/\.usage-detail-page \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(page).toMatch(/\.usage-detail-page__capacity-tab \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;/);
  });

  it('makes every detail tab fill the available horizontal content area', () => {
    const page = source('src/pages/usage/UsageDetailPage.vue');

    expect(page).toMatch(/\.usage-detail-page__tabs :deep\(\.el-tab-pane\) \{\r?\n  flex: 1 1 auto;\r?\n  min-width: 0;\r?\n  width: 100%;/);
  });
});
