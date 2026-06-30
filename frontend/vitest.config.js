import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./test/setup.js'],
    include: ['test/**/*.test.js'],
    coverage: {
      provider: 'v8',
      all: true,
      include: ['src/**/*.{js,vue}'],
      exclude: [
        'src/assets/**',
        'src/styles/**',
        'src/main.js',
      ],
      thresholds: {
        lines: 70,
        branches: 70,
        statements: 70,
      },
    },
  },
});
