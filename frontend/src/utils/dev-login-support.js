import { setToken } from '@/utils/authorization';

export function enableLoginSupport() {
  if (import.meta.env.DEV) {
    const urlParams = new URLSearchParams(location.search);
    const token = urlParams.get('_token');

    if (token) {
      setToken(token);
    }
  }
}

export function isInIframe() {
  return window.parent !== window;
}
