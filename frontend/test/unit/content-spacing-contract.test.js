import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const frontendRoot = resolve(import.meta.dirname, '../..');

const readFrontendSource = (relativePath) =>
  readFileSync(resolve(frontendRoot, relativePath), 'utf8').replace(/\r\n/g, '\n');

function extractBlocks(source, selector) {
  const blocks = [];
  let cursor = 0;

  while ((cursor = source.indexOf(selector, cursor)) !== -1) {
    const openBrace = source.indexOf('{', cursor + selector.length);
    if (openBrace === -1) break;

    let depth = 1;
    let index = openBrace + 1;
    for (; index < source.length && depth > 0; index += 1) {
      if (source[index] === '{') depth += 1;
      if (source[index] === '}') depth -= 1;
    }

    if (depth === 0) blocks.push(source.slice(openBrace + 1, index - 1));
    cursor = index;
  }

  return blocks;
}

function directDeclarations(block) {
  let depth = 0;
  let directSource = '';

  for (const character of block) {
    if (character === '{') depth += 1;
    if (depth === 0) directSource += character;
    if (character === '}') depth -= 1;
  }

  return directSource;
}

const hasOuterPaddingDeclaration = (source) =>
  /(^|[;\s])padding(?:-(?:top|right|bottom|left))?\s*:/m.test(source);

// Review source: the incident center route expanded the active page set without updating this matrix.
// Resolution: list the route explicitly so additions remain intentional and the exact-count contract stays useful.
const expectedInUsePageComponents = [
  '@/pages/admin/aggregate/AggregateDetailPage.vue',
  '@/pages/admin/aggregate/AggregateListPage.vue',
  '@/pages/admin/ai/AiAuditDetailPage.vue',
  '@/pages/admin/ai/AiCenterPage.vue',
  '@/pages/admin/audit/AuditEventDetailPage.vue',
  '@/pages/admin/audit/AuditEventListPage.vue',
  '@/pages/admin/qtree/QtreeDetailPage.vue',
  '@/pages/admin/qtree/QtreeListPage.vue',
  '@/pages/admin/settings/SettingsPage.vue',
  '@/pages/admin/storage-cluster/StorageClusterDetailPage.vue',
  '@/pages/admin/storage-cluster/StorageClusterListPage.vue',
  '@/pages/admin/user/UserListPage.vue',
  '@/pages/admin/volume/VolumeDetailPage.vue',
  '@/pages/admin/volume/VolumeListPage.vue',
  '@/pages/ai/AiChatPage.vue',
  '@/pages/alert/AlertListPage.vue',
  '@/pages/dashboard/DashboardPage.vue',
  '@/pages/group-tag/GroupTagListPage.vue',
  '@/pages/group/GroupDetailPage.vue',
  '@/pages/group/GroupListPage.vue',
  '@/pages/incident/IncidentCenterPage.vue',
  '@/pages/project/ProjectDetailPage.vue',
  '@/pages/project/ProjectListPage.vue',
  '@/pages/usage/UsageDetailPage.vue',
  '@/pages/usage/UsageListPage.vue',
];

const excludedPageComponents = [
  '@/pages/admin/backup/BackUpListPage.vue',
  '@/pages/auth/LoginPage.vue',
  '@/pages/error/NotFoundPage.vue',
  '@/pages/error/UnauthorizedPage.vue',
];

describe('application shell content spacing contract', () => {
  it('replaces the utility wrap gutter with a stable content-wrap class', () => {
    const source = readFrontendSource('src/layouts/AppLayout.vue');

    expect(source).not.toContain('wrap-class="px-4"');
    expect(source).toContain('wrap-class="app-main__content-wrap"');
  });

  it('owns desktop and mobile four-side content-wrap padding in AppLayout SCSS', () => {
    const source = readFrontendSource('src/layouts/AppLayout.vue');

    expect(source).toMatch(
      /:deep\(\.app-main__content-wrap\)\s*{[^}]*padding:\s*var\(--spacing-lg\)/s,
    );
    expect(source).toMatch(
      /(?:@include\s+mobile|@media\s*\(max-width:\s*768px\))\s*{[\s\S]*?:deep\(\.app-main__content-wrap\)\s*{[^}]*padding:\s*var\(--spacing-md\)/,
    );
  });

  it('explicitly resets app-main padding and gives the breadcrumb matching independent padding', () => {
    const source = readFrontendSource('src/layouts/AppLayout.vue');
    const appMain = directDeclarations(extractBlocks(source, '.app-main')[0]);
    const appMainPadding = [...appMain.matchAll(
      /padding(?:-(?:left|right))?\s*:\s*([^;]+);/g,
    )].map((match) => match[1].trim());

    expect(appMainPadding).toEqual(['0']);

    const breadcrumb = directDeclarations(extractBlocks(source, '.py-4')[0]);
    expect(breadcrumb).toMatch(/padding-left:\s*var\(--spacing-lg\)/);
    expect(breadcrumb).toMatch(/padding-right:\s*var\(--spacing-lg\)/);
    expect(source).toMatch(
      /(?:@include\s+mobile|@media\s*\(max-width:\s*768px\))\s*{[\s\S]*?\.py-4\s*{[^}]*padding-left:\s*var\(--spacing-md\)[^}]*padding-right:\s*var\(--spacing-md\)/,
    );
  });
});

describe('shared page layout spacing contract', () => {
  it.each([
    ['src/styles/page-layout.scss', '[class$="-list-page"],\n[class$="-page"]'],
    ['src/styles/mixins.scss', '@mixin page-container'],
  ])('%s retains layout flow without owning outer padding', (relativePath, selector) => {
    const source = readFrontendSource(relativePath);
    const block = extractBlocks(source, selector)[0];

    expect(block).toBeDefined();
    expect(block).toMatch(/display:\s*flex/);
    expect(block).toMatch(/flex-direction:\s*column/);
    expect(block).toMatch(/gap:\s*var\(--spacing-md\)/);
    expect(block).toMatch(/height:\s*100%/);
    expect(extractBlocks(source, selector).every((candidate) =>
      !hasOuterPaddingDeclaration(directDeclarations(candidate)),
    )).toBe(true);
  });
});

describe('in-use routed page matrix', () => {
  it('covers exactly the 25 approved page components and excludes inactive shells', () => {
    const routesSource = readFrontendSource('src/router/routes.js');
    const routedComponents = [...routesSource.matchAll(
      /component:\s*\(\)\s*=>\s*import\(['"](@\/pages\/[^'"]+\.vue)['"]\)/g,
    )].map((match) => match[1]);
    const inUseComponents = routedComponents
      .filter((component) => !excludedPageComponents.includes(component))
      .sort();

    expect(inUseComponents).toHaveLength(25);
    expect(inUseComponents).toEqual(expectedInUsePageComponents);
    expect(routedComponents.filter((component) => excludedPageComponents.includes(component)).sort())
      .toEqual([...excludedPageComponents].sort());
  });
});

describe('page-level spacing exceptions', () => {
  it('removes all outer padding declarations from the Dashboard root', () => {
    const dashboardSource = readFrontendSource('src/pages/dashboard/DashboardPage.vue');
    const dashboardRoots = extractBlocks(dashboardSource, '.dashboard-page')
      .map(directDeclarations);

    expect(dashboardRoots.length).toBeGreaterThan(0);
    expect(dashboardRoots.every((block) => !hasOuterPaddingDeclaration(block))).toBe(true);
  });

  it('removes the extra top margin from the storage cluster overview card', () => {
    const storageClusterDetailSource = readFrontendSource(
      'src/pages/admin/storage-cluster/StorageClusterDetailPage.vue',
    );

    expect(storageClusterDetailSource).not.toMatch(
      /<ElCard[\s\S]*?class="[^"]*\bmt-2\.5\b[^"]*"/,
    );
  });

  it('lets AI Chat fill its parent without viewport-based height calculations', () => {
    const aiChatSource = readFrontendSource('src/pages/ai/AiChatPage.vue');
    const aiWorkspace = directDeclarations(extractBlocks(aiChatSource, '.ai-workspace')[0]);

    expect.soft(aiChatSource).not.toContain('height: calc(100vh - 180px)');
    expect.soft(aiWorkspace).toMatch(/height:\s*100%/);
    expect.soft(aiWorkspace).toMatch(/min-height:\s*0/);
  });

  it('removes the standalone bottom padding from the AI Center root', () => {
    const aiCenterSource = readFrontendSource('src/pages/admin/ai/AiCenterPage.vue');
    const aiCenter = directDeclarations(extractBlocks(aiCenterSource, '.ai-center')[0]);

    expect(aiCenter).not.toMatch(/padding-bottom\s*:/);
  });
});

describe('component internal spacing preservation guards', () => {
  it('keeps intentional component padding and dashboard rhythm intact', () => {
    const queryFormSource = readFrontendSource('src/components/form/QueryForm.vue');
    const dataTableSource = readFrontendSource('src/components/data/DataTable.vue');
    const writeFormSource = readFrontendSource('src/styles/write-form.scss');
    const projectListSource = readFrontendSource('src/pages/project/ProjectListPage.vue');
    const dashboardSource = readFrontendSource('src/pages/dashboard/DashboardPage.vue');

    expect(queryFormSource).toMatch(
      /\.query-form-bar\s*{[^}]*padding:\s*var\(--spacing-md\) var\(--spacing-xl\)/s,
    );
    expect(dataTableSource).toMatch(
      /\.el-card__body\s*{[^}]*padding:\s*var\(--spacing-md\) var\(--spacing-xl\)/s,
    );
    expect(writeFormSource).toMatch(
      /\.write-form-dialog[\s\S]*?\.el-dialog__body\s*{[^}]*padding:\s*var\(--spacing-xl\)/,
    );
    expect(projectListSource).toMatch(
      /\.el-tabs__content\s*{[^}]*padding:\s*var\(--spacing-lg\) 0 0/s,
    );
    expect(dashboardSource).toMatch(
      /\.dashboard-grid\s*{[^}]*gap:\s*var\(--spacing-xl\)/s,
    );
  });
});
