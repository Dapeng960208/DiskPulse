import baseRequest from './base-request';
import { appendUrl } from '@/utils';

function wrapResponse(request) {
  return new Promise((resolve, reject) => {
    request.then((response) => resolve(response.data)).catch(reject);
  });
}

// 从 Content-Disposition 响应头中解析文件名（优先 RFC 5987 的 filename*）
function extractFilename(response) {
  const disposition = response?.headers?.['content-disposition'];
  if (!disposition) return '';
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch {
      return utf8Match[1];
    }
  }
  const asciiMatch = /filename="?([^";]+)"?/i.exec(disposition);
  return asciiMatch ? asciiMatch[1] : '';
}

class BaseApi {
  constructor(urlPrefix, request) {
    this.request = request || baseRequest;
    this.urlPrefix = urlPrefix;
  }

  $all(...apis) {
    return this.request.all(apis);
  }

  $spread(callback) {
    return this.request.spread(callback);
  }

  $post(url, data, config) {
    return this.request.post(url, data, config);
  }

  $delete(url, config) {
    return this.request.delete(url, config);
  }

  $put(url, data, config) {
    return this.request.put(url, data, config);
  }

  $patch(url, data, config) {
    return this.request.patch(url, data, config);
  }

  $get(url, config) {
    return this.request.get(url, config);
  }

  addPrefix(url) {
    // 空 url 直接返回 prefix（避免 appendUrl 添加尾斜杠）
    if (!url) return this.urlPrefix;
    // 使用 appendUrl 规范化路径拼接，避免双斜杠或缺斜杠
    return appendUrl(this.urlPrefix, url);
  }

  post(url, data, config) {
    return wrapResponse(this.request.post(this.addPrefix(url), data, config));
  }

  delete(url, config) {
    return wrapResponse(this.request.delete(this.addPrefix(url), config));
  }

  put(url, data, config) {
    return wrapResponse(this.request.put(this.addPrefix(url), data, config));
  }

  patch(url, data, config) {
    return wrapResponse(this.request.patch(this.addPrefix(url), data, config));
  }

  get(url, queryParams, config) {
    return wrapResponse(
      this.request.get(this.addPrefix(url), {
        params: queryParams,
        ...config,
      }),
    );
  }

  export(url, params, config) {
    return this.request.get(this.addPrefix(url), {
      ...config,
      params,
      responseType: 'blob',
    });
  }

  download(url, params, config) {
    // 通过带鉴权头的 blob 请求获取文件，避免把 Bearer token 暴露在 URL 中
    // （URL 中的 token 会泄露到浏览器历史、服务端访问日志、代理日志和 Referer 头）。
    return this.request
      .get(this.addPrefix(url), {
        ...config,
        params,
        responseType: 'blob',
      })
      .then((response) => {
        const blob = response.data instanceof Blob
          ? response.data
          : new Blob([response.data]);
        const objectUrl = window.URL.createObjectURL(blob);
        return () => {
          const anchor = document.createElement('a');
          anchor.href = objectUrl;
          anchor.download = extractFilename(response) || '';
          document.body.appendChild(anchor);
          anchor.click();
          document.body.removeChild(anchor);
          // 触发下载后释放 object URL，避免内存泄漏
          window.URL.revokeObjectURL(objectUrl);
        };
      });
  }
}

export default BaseApi;
