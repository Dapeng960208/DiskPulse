import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useBreadcrumbs = defineStore('breadcrumbs', () => {
  const detailTitles = ref({});
  const detailBreadcrumbs = ref({});

  function setDetailTitle(routeName, title) {
    detailTitles.value = { ...detailTitles.value, [routeName]: title || '' };
  }

  function detailTitleFor(routeName) {
    return detailTitles.value[routeName] || '';
  }

  function setDetailBreadcrumb(routeName, labels) {
    detailBreadcrumbs.value = {
      ...detailBreadcrumbs.value,
      [routeName]: Array.isArray(labels) ? labels.filter(Boolean) : [],
    };
  }

  function detailBreadcrumbFor(routeName) {
    return detailBreadcrumbs.value[routeName] || [];
  }

  return { setDetailTitle, detailTitleFor, setDetailBreadcrumb, detailBreadcrumbFor };
});
