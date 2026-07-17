export function buildBreadcrumbItems(matchedRoutes = []) {
  const currentRoute = matchedRoutes.at(-1);
  const declaredBreadcrumb = currentRoute?.meta?.breadcrumb;

  if (Array.isArray(declaredBreadcrumb) && declaredBreadcrumb.length > 0) {
    return declaredBreadcrumb;
  }

  return matchedRoutes
    .map((route) => route.meta?.title)
    .filter(Boolean);
}
