import RequestBuilder from './request-builder';

export default new RequestBuilder({
  baseURL: import.meta.env.VITE_APP_API_BASE_URL,
  timeout: import.meta.env.VITE_REQUEST_TIMEOUT,
}).build();
