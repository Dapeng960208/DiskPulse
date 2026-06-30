import { join } from 'path';
import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';
import unoCSS from 'unocss/vite';
import vueJsx from '@vitejs/plugin-vue-jsx';
import elementPlus from 'unplugin-element-plus/vite';
import { version } from './package.json';

// https://vitejs.dev/config/
export default ({ mode }) => {
  process.env = {
    ...process.env,
    ...loadEnv(mode, process.cwd()),
  };

  return defineConfig({
    base: process.env.VITE_APP_BASE || '/',
    resolve: {
      alias: {
        '@': '/src',
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          // 全局注入变量和混入，无需在每个文件单独 @import
          additionalData: `@use "@/styles/variables.scss" as *; @use "@/styles/mixins.scss" as *;`,
          // 沉默弃用警告
          silenceDeprecations: ['legacy-js-api', 'import'],
        },
      },
    },
    plugins: [
      vue(),
      vueJsx(),
      unoCSS(),
      elementPlus(),
    ],
    build: {
      target: 'esnext',
      outDir: join('builds', mode, `v${version}`),
    },
  });
};
