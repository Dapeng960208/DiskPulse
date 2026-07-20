export function buildBreadcrumbItems(matchedRoutes = [], detailTitle = '', detailBreadcrumb = []) {
  const currentRoute = matchedRoutes.at(-1);
  const declaredBreadcrumb = currentRoute?.meta?.breadcrumb;
  const hasDetailBreadcrumb = Array.isArray(detailBreadcrumb) && detailBreadcrumb.length > 0;
  const labels = hasDetailBreadcrumb
    ? [...detailBreadcrumb]
    : Array.isArray(declaredBreadcrumb) && declaredBreadcrumb.length > 0
      ? [...declaredBreadcrumb]
      : matchedRoutes
        .map((route) => route.meta?.title)
        .filter(Boolean);

  if (!hasDetailBreadcrumb && detailTitle && labels.length > 0) {
    labels[labels.length - 1] = `${detailTitle}详情`;
  }

  return labels.map((label) => ({ label, title: label }));
}
