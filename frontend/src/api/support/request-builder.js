import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';
import router from '@/router';
import { toLoginPage } from '@/utils';
import { getToken, removeToken } from '@/utils/authorization';
import { mockAxiosAdapter, mockEnabled } from '@/mocks/runtime';

// 防抖登出重定向，避免并发 401 触发多次跳转
let redirecting = false;
function debouncedLoginRedirect() {
  if (redirecting) return;
  redirecting = true;
  removeToken();
  setTimeout(() => {
    toLoginPage();
    redirecting = false;
  }, 100);
}

class RequestBuilder {
  constructor(options) {
    this.options = options;
  }

  build() {
    // create an axios instance
    const service = axios.create({ ...this.options, ...(mockEnabled() ? { adapter: mockAxiosAdapter } : {}) });

    // request interceptor
    service.interceptors.request.use(
      (config) => {
        const token = getToken();
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
      },
      (error) => {
        console.error(error); // for debug
        return Promise.reject(error);
      },
    );

    // response interceptor
    service.interceptors.response.use(
      (response) => response,
      (error) => {
        // 处理网络错误或无响应的情况
        if (!error.response) {
          console.error('Network Error:', error.message);
          ElMessage.error('网络连接失败，请检查网络设置');
          return Promise.reject(error);
        }

        // Mock adapters can reject before Axios attaches config; preserve the original 401/403 instead of crashing the UI.
        if (!error.config?.errorHandlerDisabled) {
          const status = error.response.status;
          const customErrorHandler = error.config?.errorHandlers?.[status];

          if (customErrorHandler) {
            customErrorHandler(error);
          } else {
            switch (status) {
              case 400: {
                if (error.config?.redirect) {
                  router.push('/400');
                  break;
                }
                ElMessage.error(error.response.data.message ||error.response.data.detail|| '请求有误');
                break;
              }
              case 401: {
                if (error.config?.redirect) {
                  router.push('/401');
                  break;
                }
                // Session 过期或未授权，清除 token 并重定向到登录页
                ElMessage.warning('登录已过期，请重新登录');
                debouncedLoginRedirect();
                break;
              }
              case 403: {
                if (error.config?.redirect) {
                  router.push('/403');
                  break;
                }
                ElMessageBox.alert(error.response.data.message || '您当前没有权限进行此操作', '没有权限', {
                  type: 'warning',
                  confirmButtonText: '我知道了',
                  showCancelButton: false,
                });
                break;
              }
              case 404: {
                ElMessage.error(error.response.data.message || '请求资源不存在');
                break;
              }
              case 500: {
                if (error.config?.redirect) {
                  router.push('/500');
                  break;
                }
                ElMessage.error(error.response.data.message || '服务器内部错误');
                break;
              }
              default:
                ElMessage.error('网络错误');
                break;
            }
          }
        } else if (error.response?.status === 401) {
          // errorHandlerDisabled 路径下的 401 也需要处理
          debouncedLoginRedirect();
        }
        return Promise.reject(error);
      },
    );

    service.all = axios.all;
    service.spread = axios.spread;

    return service;
  }
}

export default RequestBuilder;
