export function buildBreadcrumbItems(matchedRoutes = [], detailTitle = '') {
  const currentRoute = matchedRoutes.at(-1);
  const declaredBreadcrumb = currentRoute?.meta?.breadcrumb;
  const labels = Array.isArray(declaredBreadcrumb) && declaredBreadcrumb.length > 0
    ? [...declaredBreadcrumb]
    : matchedRoutes
      .map((route) => route.meta?.title)
      .filter(Boolean);

  if (detailTitle && labels.length > 0) {
    labels[labels.length - 1] = `${detailTitle}详情`;
  }

  return labels.map((label) => ({ label, title: label }));
}
