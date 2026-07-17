import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useBreadcrumbs = defineStore('breadcrumbs', () => {
  const detailTitles = ref({});

  function setDetailTitle(routeName, title) {
    detailTitles.value = { ...detailTitles.value, [routeName]: title || '' };
  }

  function detailTitleFor(routeName) {
    return detailTitles.value[routeName] || '';
  }

  return { setDetailTitle, detailTitleFor };
});
