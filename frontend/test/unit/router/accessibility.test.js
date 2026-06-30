import { processRoutes, resolveAccessibility, shouldUpdatePageSubtitle } from '@/router/support/accessibility';

describe('router/support/accessibility', () => {
  it('returns 200 when accessibility is omitted', () => {
    expect(resolveAccessibility()).toBe(200);
  });

  it('accepts only supported accessibility codes from functions', () => {
    expect(resolveAccessibility(() => 403)).toBe(403);
    expect(() => resolveAccessibility(() => 500)).toThrow(/200, 401 or 403/);
  });

  it('wraps child routes with parent accessibility', () => {
    const routes = [
      {
        meta: {
          isAccessible: () => 403,
        },
        children: [
          {
            meta: {},
          },
        ],
      },
    ];

    processRoutes(routes);

    expect(routes[0].meta.isAccessible()).toBe(403);
    expect(routes[0].children[0].meta.isAccessible()).toBe(403);
  });

  it('delegates subtitle updates when route meta hook allows it', () => {
    const updater = vi.fn();
    shouldUpdatePageSubtitle(
      {
        meta: {
          title: 'Dashboard',
          shouldUpdatePageSubtitle: () => true,
        },
      },
      { meta: {} },
      updater,
    );

    expect(updater).toHaveBeenCalledWith('Dashboard');
  });
});
