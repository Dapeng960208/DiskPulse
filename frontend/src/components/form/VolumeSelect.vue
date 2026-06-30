<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import volumeApi from '@/api/volume-api';
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

const volumeOptions = ref([]);
const searchingUserGroups = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  volumeOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((volumeId) => {
    volumeApi.fetchById(volumeId).then((result) => {
      volumeOptions.value.push(result);
    });
  });

  if (volumeOptions.value.length === 0) {
    volumeApi.fetch({ page: 1, size: 20 }).then((result) => {
      volumeOptions.value = result.content;
    });
  }
}

function searchUserGroups(queryString) {
  if (queryString) {
    searchingUserGroups.value = true;
    volumeApi.fetch({
      nameLike: queryString,
    }).then((result) => {
      volumeOptions.value = result.content;
    }).finally(() => (searchingUserGroups.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingUserGroups"
    :remote-method="searchUserGroups"
    placeholder="根据Volume模糊搜索"
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
      v-for="volumeOption of volumeOptions"
      :key="volumeOption.id"
      :label="volumeOption.name"
      :value="volumeOption.id"
    >
    </ElOption>
  </ElSelect>
</template>
