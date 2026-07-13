<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import { useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: Number,
    default: null,
  },
  projectId: {
    type: Number,
    default: null,
  },
  clearable: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(['update:modelValue']);
const { model } = useSelectModel(props, emit);
const environmentOptions = ref([]);
const loading = ref(false);

watch(() => props.projectId, loadOptions, { immediate: true });

async function loadOptions(projectId) {
  environmentOptions.value = [];
  if (!projectId) return;
  loading.value = true;
  try {
    const { default: environmentApi } = await import(
      '@/api/project-storage-environment-api'
    );
    const result = await environmentApi.fetchByProject(projectId, {
      page: 1,
      size: 100,
    });
    environmentOptions.value = result.content;
  } catch {
    environmentOptions.value = [];
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="loading"
    :disabled="!projectId"
    :clearable="clearable"
    placeholder="请选择存储环境">
    <ElOption
      v-for="environment in environmentOptions"
      :key="environment.id"
      :label="environment.name"
      :value="environment.id" />
  </ElSelect>
</template>
