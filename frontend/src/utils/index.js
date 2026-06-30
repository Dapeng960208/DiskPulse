export function toLoginPage() {
  // 使用内部登录页面而不是外部URL
  const currentPath = window.location.pathname + window.location.search;
  const loginUrl = `/login?redirect=${encodeURIComponent(currentPath)}`;

  // 如果已经在登录页，不需要重定向
  if (window.location.pathname === '/login') {
    return;
  }

  window.location.href = loginUrl;
}

export function updatePageSubtitle(subtitle) {
  if (subtitle && typeof subtitle === 'string') {
    subtitle
      = subtitle.length > 50 ? `${subtitle.substring(0, 47)}...` : subtitle;
    document.title = `${subtitle} - ${import.meta.env.VITE_APP_TITLE}`;
  } else {
    document.title = import.meta.env.VITE_APP_TITLE;
  }
}

export function debounce(fn, delay) {
  let timer = null;
  return (immediate, ...parameters) => {
    if (timer) {
      clearTimeout(timer);
    }

    if (immediate) {
      fn(...parameters);
    } else {
      timer = setTimeout(() => fn(...parameters), delay);
    }
  };
}

export function appendUrl(url, segment) {
  const urlEndsWithSlash = url.endsWith('/');
  const segmentStartsWithSlash = segment.startsWith('/');

  if (urlEndsWithSlash && segmentStartsWithSlash) {
    return url + segment.substring(1);
  } else if (urlEndsWithSlash || segmentStartsWithSlash) {
    return url + segment;
  } else {
    return `${url}/${segment}`;
  }
}

export function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }

  return array;
}

export function isWithin7Days(date) {
  const today = new Date();
  return date.getTime() > today.setDate(today.getDate() - 7);
}

/**
 * 将普通对象转化为 UrlSearchParams。
 *
 * @param {Object} queryParams
 */
export function parseUrlSearchParams(queryParams) {
  const urlSearchParams = new URLSearchParams();

  for (const key in queryParams) {
    // 以 `__` 开头的字段会被忽略
    if (key.startsWith('__')) {
      continue;
    }

    let name = key;
    const value = queryParams[key];
    const matches = /(.*)(\$\d+)$/.exec(key);

    if (matches) {
      name = matches[1];
    }

    if (value !== undefined) {
      // 检查是否是数组
      if (Array.isArray(value)) {
        value.forEach(item => urlSearchParams.append(name, item));
      } else {
        urlSearchParams.append(name, value);
      }
    }
  }

  return urlSearchParams;
}

/**
 *
 * @param {String} html
 * @returns
 */
export function escapeHtml(html) {
  return html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
