<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect } from 'element-plus';
import projectApi from '@/api/project-api';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [Number, Array,String],
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
  placeholder: {
    type: String,
    default: '根据项目名搜索',
  },
});
const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const projectOptions = ref([]);
const searchingProjects = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  projectOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((projectId) => {
    projectApi.fetchById(projectId).then((result) => {
      projectOptions.value.push(result);
    });
  });

  if (projectOptions.value.length === 0) {
    projectApi.fetch({ page: 1, size: 20 }).then((result) => {
      projectOptions.value = result.content;
    });
  }
}

function searchProjects(queryString) {
  if (queryString) {
    searchingProjects.value = true;
    projectApi.fetch({
      nameLike: queryString,
    }).then((result) => {
      projectOptions.value = result.content;
    }).finally(() => (searchingProjects.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingProjects"
    :remote-method="searchProjects"
    :placeholder="placeholder"
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
      v-for="projectOption of projectOptions"
      :key="projectOption.id"
      :label="projectOption.name"
      :value="projectOption.id"
    >
    </ElOption>
  </ElSelect>
</template>
