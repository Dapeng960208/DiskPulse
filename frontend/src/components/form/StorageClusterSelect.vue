<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import storageClusterApi from '@/api/storage-cluster-api';
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
});
const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const clusterOptions = ref([]);
const searching = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  clusterOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((clusterId) => {
    storageClusterApi.fetchById(clusterId).then((result) => {
      clusterOptions.value.push(result);
    });
  });

  if (clusterOptions.value.length === 0) {
    storageClusterApi.fetch({ page: 1, size: 20 }).then((result) => {
      clusterOptions.value = result.content;
    });
  }
}

function searchClusters(queryString) {
  if (queryString) {
    searching.value = true;
    storageClusterApi.fetch({
      nameLike: queryString,
    }).then((result) => {
      clusterOptions.value = result.content;
    }).finally(() => (searching.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searching"
    :remote-method="searchClusters"
    placeholder="根据存储集群模糊搜索"
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
  >
    <ElOption
      v-for="clusterOption of clusterOptions"
      :key="clusterOption.id"
      :label="clusterOption.name"
      :value="clusterOption.id"
    >
    </ElOption>
  </ElSelect>
</template>
