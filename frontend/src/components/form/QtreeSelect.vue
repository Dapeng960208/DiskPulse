<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace, ElTag } from 'element-plus';
import qtreeApi from '@/api/qtree-api';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [Number, Array],
    default: null,
  },
  multiple: {
    type: Boolean,
    default: false,
  },
  multipleLimit: {
    type: Number,
    default: null,
  },
  clearable: {
    type: Boolean,
    default: false,
  },
  volumeId:{
    type:Number,
    default:null
  },
  storageClusterId: {
    type: Number,
    default: null,
  },
});
const emit = defineEmits(['update:modelValue', 'selected-label-change']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const qtreeOptions = ref([]);
const searchingQtree = ref(false);

watch(
  [normalizedModelValue, () => props.volumeId, () => props.storageClusterId],
  ([selectedValue]) => initDefaultOptions(selectedValue),
  { immediate: true },
);

function queryParams(extra = {}) {
  return {
    page: 1,
    size: 20,
    ...(props.volumeId ? { volume_id: props.volumeId } : {}),
    ...(props.storageClusterId ? { storage_cluster_id: props.storageClusterId } : {}),
    ...extra,
  };
}

function initDefaultOptions(selectedValue) {
  qtreeOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((qtreeId) => {
    qtreeApi.fetchById(qtreeId).then((result) => {
      qtreeOptions.value.push(result);
    });
  });

  if (qtreeOptions.value.length === 0) {
    qtreeApi.fetch(queryParams()).then((result) => {
      qtreeOptions.value = result.content;
    });
  }
}

function searchQtree(queryString) {
  if (queryString) {
    searchingQtree.value = true;
    qtreeApi.fetch(queryParams({ nameLike: queryString })).then((result) => {
      qtreeOptions.value = result.content;
    }).finally(() => (searchingQtree.value = false));
  }
}

function emitSelectedLabel(value) {
  const labels = toSelectValues(value, props.multiple).map((id) => {
    const option = qtreeOptions.value.find((item) => item.id === id);
    return option?.volume ? `${option.volume.name}/${option.name}` : option?.name;
  }).filter(Boolean);
  emit('selected-label-change', labels.length ? labels.join('、') : null);
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingQtree"
    :remote-method="searchQtree"
    placeholder="根据 Qtree（NetApp）模糊搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    :max-collapse-tags="10"
    :clearable="clearable"
    default-first-option
    filterable
    remote
    remote-show-suffix
    collapse-tags
    collapse-tags-tooltip
    @change="emitSelectedLabel"
  >
    <ElOption
      v-for="qtreeOption of qtreeOptions"
      :key="qtreeOption.id"
      :label="qtreeOption.volume? `${qtreeOption.volume.name}/${qtreeOption.name}`:qtreeOption.name"
      :value="qtreeOption.id"
    >
      <div class="flex justify-between items-center">
        <ElTag v-if="qtreeOption.volume">{{ qtreeOption.volume?.name }}</ElTag>
        <ElSpace>
          {{ qtreeOption.name }}
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
