import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

describe('project realtime usage layout', () => {
  it('gives the realtime tab an explicit flex height root so its workspace fills the content area', () => {
    const component = source('src/pages/project/components/ProjectDiskUsage.vue');

    expect(component).toContain('<section class="project-disk-usage">');
    expect(component).toContain('class="project-disk-usage__content"');
    expect(component).toMatch(/\.project-disk-usage \{\r?\n  display: flex;\r?\n  flex: 1 1 auto;\r?\n  flex-direction: column;\r?\n  min-height: 0;\r?\n  height: 100%;/);
    expect(component).toMatch(/\.project-disk-usage__content \{\r?\n  flex: 1 1 auto;\r?\n  min-height: 0;\r?\n  height: 100%;/);
  });
});
