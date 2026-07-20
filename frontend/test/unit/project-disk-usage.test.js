import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('ProjectDiskUsage', () => {
  it('keeps the project usage realtime view while fixing its project context', () => {
    const source = readFileSync(resolve('src/pages/project/components/ProjectDiskUsage.vue'), 'utf8');
    const realTimePage = readFileSync(resolve('src/pages/common/RealTimePage.vue'), 'utf8');

    expect(source).toContain("import RealTimePage from '@/pages/common/RealTimePage.vue'");
    expect(source).toContain('api-type="project"');
    expect(source).toContain(':show-resource-select="!attributeId"');
    expect(source).toContain(':allowed-indicators="[\'used\']"');
    expect(source).toContain(':fill-content="Boolean(attributeId)"');
    expect(realTimePage).toContain('label="时间范围"');
    expect(realTimePage).toContain('v-if="showResourceSelect && selectedSelect"');
    expect(realTimePage).toContain('fillContent');
    expect(realTimePage).toContain('real-time-page--fill');
  });
});
