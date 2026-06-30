import {
  appendUrl,
  debounce,
  escapeHtml,
  isWithin7Days,
  parseUrlSearchParams,
  shuffleArray,
  toLoginPage,
  updatePageSubtitle,
} from '@/utils';

describe('utils/index', () => {
  it('updates the page title when a subtitle is provided', () => {
    updatePageSubtitle('Dashboard');
    expect(document.title).toContain('Dashboard');
  });

  it('redirects to login with encoded current path', () => {
    const { location } = window;
    delete window.location;
    window.location = {
      href: '',
      pathname: '/usage',
      search: '?page=2',
    };

    toLoginPage();

    expect(window.location.href).toBe('/login?redirect=%2Fusage%3Fpage%3D2');
    window.location = location;
  });

  it('appends URL segments without duplicate slashes', () => {
    expect(appendUrl('/api', 'users')).toBe('/api/users');
    expect(appendUrl('/api/', '/users')).toBe('/api/users');
  });

  it('debounces deferred calls and supports immediate mode', async () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const wrapped = debounce(fn, 100);

    wrapped(false, 'first');
    wrapped(false, 'second');
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledWith('second');

    wrapped(true, 'third');
    expect(fn).toHaveBeenCalledWith('third');
    vi.useRealTimers();
  });

  it('parses search params while skipping private keys', () => {
    const params = parseUrlSearchParams({
      page: 1,
      tags: ['a', 'b'],
      '__internal': true,
      'type$1': 'ssd',
    });

    expect(params.getAll('tags')).toEqual(['a', 'b']);
    expect(params.get('page')).toBe('1');
    expect(params.get('type')).toBe('ssd');
    expect(params.get('__internal')).toBeNull();
  });

  it('escapes HTML and keeps arrays shuffled in place', () => {
    const source = [1, 2, 3, 4];
    const shuffled = shuffleArray(source);

    expect(shuffled).toBe(source);
    expect(shuffled).toHaveLength(4);
    expect(escapeHtml('<div>&</div>')).toBe('&lt;div&gt;&amp;&lt;/div&gt;');
  });

  it('checks whether a date is within seven days', () => {
    const recent = new Date(Date.now() - 2 * 24 * 3600 * 1000);
    const old = new Date(Date.now() - 10 * 24 * 3600 * 1000);

    expect(isWithin7Days(recent)).toBe(true);
    expect(isWithin7Days(old)).toBe(false);
  });
});
