<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import groupTagApi from '@/api/group-tag-api';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: { type: [Number, Array], default: null },
  multiple: { type: Boolean, default: false },
  clearable: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue', 'selected-label-change']);
const { model, normalizedModelValue } = useSelectModel(props, emit);
const options = ref([]);
const loading = ref(false);

watch(normalizedModelValue, async (selectedValue) => {
  options.value = [];
  const values = toSelectValues(selectedValue, props.multiple);
  if (values.length) {
    options.value = await Promise.all(values.map((id) => groupTagApi.fetchById(id)));
    return;
  }
  const result = await groupTagApi.fetch({ page: 1, size: 20 });
  options.value = result.content;
}, { immediate: true });

async function search(query) {
  loading.value = true;
  try {
    const result = await groupTagApi.fetch({ nameLike: query || null, page: 1, size: 20 });
    options.value = result.content;
  } finally {
    loading.value = false;
  }
}

function emitSelectedLabel(value) {
  const labels = toSelectValues(value, props.multiple)
    .map((id) => options.value.find((option) => option.id === id)?.name)
    .filter(Boolean);
  emit('selected-label-change', labels.length ? labels.join('、') : null);
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :multiple="multiple"
    :clearable="clearable"
    :loading="loading"
    :remote-method="search"
    placeholder="请选择项目组标签"
    filterable
    remote
    @change="emitSelectedLabel">
    <ElOption
      v-for="option in options"
      :key="option.id"
      :label="option.name"
      :value="option.id" />
  </ElSelect>
</template>
