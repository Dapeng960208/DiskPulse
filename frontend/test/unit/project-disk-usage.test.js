import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('ProjectDiskUsage', () => {
  it('restores the project trend with time filtering and usage as the only indicator', () => {
    const source = readFileSync(resolve('src/pages/project/components/ProjectDiskUsage.vue'), 'utf8');
    const realTimePage = readFileSync(resolve('src/pages/common/RealTimePage.vue'), 'utf8');

    expect(source).toContain("import RealTimePage from '@/pages/common/RealTimePage.vue'");
    expect(source).toContain('api-type="project"');
    expect(source).toContain(':show-resource-select="false"');
    expect(source).toContain(':allowed-indicators="[\'used\']"');
    expect(realTimePage).toContain('label="时间范围"');
    expect(realTimePage).toContain('v-if="showResourceSelect && selectedSelect"');
  });
});
