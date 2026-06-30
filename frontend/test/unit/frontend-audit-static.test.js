import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

function listVueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);

    if (entry.isDirectory()) {
      return listVueFiles(path);
    }

    return entry.name.endsWith('.vue') ? [path] : [];
  });
}

describe('frontend audit static contracts', () => {
  it('routes ECharts usage through the lazy shared library', () => {
    const chartFiles = listVueFiles('src/common/charts');

    expect(chartFiles.length).toBeGreaterThan(0);

    const directImports = chartFiles.filter((file) => {
      const source = readFileSync(file, 'utf8');

      return source.includes("from 'echarts'") || source.includes('from "echarts"');
    });

    expect(directImports).toEqual([]);
  });

  it('splits vendor libraries so the app shell is not bundled with ECharts', () => {
    const source = readFileSync('vite.config.js', 'utf8');

    expect(source).toContain('manualChunks');
    expect(source).toContain('vue-vendor');
    expect(source).toContain('element-plus');
    expect(source).toContain('echarts');
  });
});
