import { defineStore } from 'pinia';
import { ref } from 'vue';
import configApi from '@/api/config-api';
import { defaultStorageAlertThresholds } from '@/utils/storage-alert-rule';

export const useStorageAlertThresholds = defineStore('storageAlertThresholds', () => {
  const thresholds = ref(defaultStorageAlertThresholds());
  const loaded = ref(false);
  let loadPromise;

  function setThresholds(value) {
    thresholds.value = {
      important: Number(value.important),
      serious: Number(value.serious),
      emergency: Number(value.emergency),
    };
    return thresholds.value;
  }

  function setFromRule(rule) {
    return setThresholds({
      important: rule.important.threshold,
      serious: rule.serious.threshold,
      emergency: rule.emergency.threshold,
    });
  }

  function load() {
    if (loaded.value) return Promise.resolve(thresholds.value);
    if (loadPromise) return loadPromise;

    loadPromise = configApi.fetchStorageAlertThresholds()
      .then(setThresholds)
      .catch(() => thresholds.value)
      .finally(() => {
        loaded.value = true;
        loadPromise = null;
      });
    return loadPromise;
  }

  return { thresholds, load, setThresholds, setFromRule };
});
