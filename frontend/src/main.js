import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { ElLoading } from 'element-plus';
import router from './router';
import App from './App.vue';
import './styles/style.scss';
import './styles/animation.css';
import './styles/page-layout.scss';
import { enableLoginSupport, isInIframe } from '@/utils/dev-login-support';
import 'normalize.css';
import 'uno.css';
import 'element-plus/theme-chalk/dark/css-vars.css';

enableLoginSupport();

if (!isInIframe()) {
  const app = createApp(App);
  const vLoading = ElLoading.directive;

  app.directive('loading', vLoading);
  app.use(router).use(createPinia()).mount('#app');
}
