import { computed, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import incidentApi from '@/api/incident-api.js';

/**
 * Composable for managing Incident AI settings
 * @returns {Object} AI settings state and methods
 */
export function useIncidentAiSettings() {
  const aiSettingsVisible = ref(false);
  const aiSettingsLoading = ref(false);
  const aiSettingsSaving = ref(false);
  const aiSettingsError = ref('');
  const aiSettings = reactive({
    enabled: false,
    model_ids: [],
    available_models: [],
    iops_absolute_floor: 10,
    iops_baseline_ratio: 0.05,
  });

  const selectedAiModels = computed(() =>
    aiSettings.model_ids
      .map((id) => aiSettings.available_models.find((model) => model.id === id))
      .filter(Boolean)
  );

  async function loadAiSettings() {
    aiSettingsLoading.value = true;
    aiSettingsError.value = '';
    try {
      const result = await incidentApi.fetchAiSettings();
      Object.assign(aiSettings, result);
    } catch (err) {
      aiSettingsError.value = err.message || '加载 AI 设置失败';
      ElMessage.error(aiSettingsError.value);
    } finally {
      aiSettingsLoading.value = false;
    }
  }

  async function saveAiSettings() {
    aiSettingsSaving.value = true;
    aiSettingsError.value = '';
    try {
      await incidentApi.updateAiSettings({
        enabled: aiSettings.enabled,
        model_ids: aiSettings.model_ids,
        iops_absolute_floor: aiSettings.iops_absolute_floor,
        iops_baseline_ratio: aiSettings.iops_baseline_ratio,
      });
      ElMessage.success('AI 设置已保存');
      aiSettingsVisible.value = false;
    } catch (err) {
      aiSettingsError.value = err.message || '保存 AI 设置失败';
      ElMessage.error(aiSettingsError.value);
    } finally {
      aiSettingsSaving.value = false;
    }
  }

  function openAiSettings() {
    aiSettingsVisible.value = true;
    loadAiSettings();
  }

  function closeAiSettings() {
    aiSettingsVisible.value = false;
    aiSettingsError.value = '';
  }

  return {
    // State
    aiSettingsVisible,
    aiSettingsLoading,
    aiSettingsSaving,
    aiSettingsError,
    aiSettings,
    selectedAiModels,

    // Methods
    loadAiSettings,
    saveAiSettings,
    openAiSettings,
    closeAiSettings,
  };
}
