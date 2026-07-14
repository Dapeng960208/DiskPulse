<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import aggregateApi from '@/api/aggregate-api';
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

const aggregateOptions = ref([]);
const searchingAggregates = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  aggregateOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((aggregateId) => {
    aggregateApi.fetchById(aggregateId).then((result) => {
      aggregateOptions.value.push(result);
    });
  });

  if (aggregateOptions.value.length === 0) {
    aggregateApi.fetch({ page: 1, size: 20 }).then((result) => {
      aggregateOptions.value = result.content;
    });
  }
}

function searchAggregates(queryString) {
  if (queryString) {
    searchingAggregates.value = true;
    aggregateApi.fetch({
      nameLike: queryString,
    }).then((result) => {
      aggregateOptions.value = result.content;
    }).finally(() => (searchingAggregates.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingAggregates"
    :remote-method="searchAggregates"
    placeholder="根据容量池模糊搜索"
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
      v-for="aggregateOption of aggregateOptions"
      :key="aggregateOption.id"
      :label="aggregateOption.name"
      :value="aggregateOption.id"
    >
    </ElOption>
  </ElSelect>
</template>
