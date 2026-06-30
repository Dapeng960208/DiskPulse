import baseRequest from './base-request';

function wrapResponse(request) {
  return new Promise((resolve, reject) => {
    request.then((response) => resolve(response.data)).catch(reject);
  });
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
    return this.urlPrefix + url;
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
    return new Promise((resolve, reject) => {
      // 先使用 HEAD 请求，判断是否有权限
      this.request
        .head(this.addPrefix(url), {
          ...config,
          params,
        })
        .then(({ config, request }) => {
          let downloadUrl = request.responseURL;

          if (config.headers.Authorization) {
            downloadUrl
              += `${downloadUrl.includes('?') ? '&' : '?'
              }authorization=${config.headers.Authorization}`;
          }

          resolve(() => (window.open(downloadUrl, '_blank')));
        })
        .catch(reject);
    });
  }
}

export default BaseApi;
