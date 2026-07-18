export function resolveAccessibility(isAccessible) {
  if (isAccessible === undefined) {
    return 200;
  }

  if (!(isAccessible instanceof Function)) {
    throw new TypeError('isAccessible must be a function');
  }

  const result = isAccessible();

  if ([200, 401, 403].includes(result)) {
    return result;
  }

  throw new Error('isAccessible() must return either 200, 401 or 403');
}

export function canAccessRoute(router, target) {
  if (!router || !target || typeof target !== 'object') return false;
  if (target.params && Object.values(target.params).some((value) => value == null || value === '')) return false;

  const resolved = router.resolve(target);
  return resolved?.meta?.isAccessible?.() === 200;
}

export function processRoutes(routes, isParentAccessible) {
  routes.forEach((route) => {
    if (!route.meta) {
      route.meta = {};
    }

    const isAccessible = route.meta.isAccessible;

    route.meta.isAccessible = () => resolveAccessibility(isAccessible);

    if (isParentAccessible) {
      route.meta.isAccessible = () => {
        const parentAccessibility = isParentAccessible();

        return parentAccessibility === 200
          ? resolveAccessibility(isAccessible)
          : parentAccessibility;
      };
    }

    if (route.children) {
      processRoutes(route.children, route.meta.isAccessible);
    }
  });
}

export function shouldUpdatePageSubtitle(to, from, updateSubtitle) {
  let canUpdateSubtitle = true;

  if (to.meta.shouldUpdatePageSubtitle) {
    canUpdateSubtitle = to.meta.shouldUpdatePageSubtitle(to, from);
  }

  if (canUpdateSubtitle) {
    updateSubtitle(to.meta.title);
  }
}
