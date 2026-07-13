<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace, ElTag } from 'element-plus';
import groupApi from '@/api/group-api';
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
  projectId:{
    type:Number,
    default:null
  },
  projectEnvironmentId: {
    type: Number,
    default: null,
  }
});
const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const groupOptions = ref([]);
const queryParams = ref({
  page:1,size:20
});
const searchingUserGroups = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });
watch(
  () => [props.projectId, props.projectEnvironmentId],
  (value, previousValue) => {
    if (previousValue && value.some((item, index) => item !== previousValue[index])) {
      emit('update:modelValue', props.multiple ? [] : null);
      initDefaultOptions(null);
    }
  },
);

function applyScope() {
  if (props.projectId) {
    queryParams.value.project_id = props.projectId;
  } else {
    delete queryParams.value.project_id;
  }
  if (props.projectEnvironmentId) {
    queryParams.value.project_environment_id = props.projectEnvironmentId;
  } else {
    delete queryParams.value.project_environment_id;
  }
}

function initDefaultOptions(selectedValue) {
  groupOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((groupId) => {
    groupApi.fetchById(groupId).then((result) => {
      groupOptions.value.push(result);
    });
  });

  if (groupOptions.value.length === 0) {
    applyScope();
    groupApi.fetch(queryParams.value).then((result) => {
      groupOptions.value = result.content;
    });
  }
}

function searchUserGroups(queryString) {
  if (queryString) {
    searchingUserGroups.value = true;
    applyScope();
    queryParams.value.nameLike = queryString;
    groupApi.fetch(queryParams.value).then((result) => {
      groupOptions.value = result.content;
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
    placeholder="根据项目组模糊搜索"
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
      v-for="groupOption of groupOptions"
      :key="groupOption.id"
      :label="groupOption.project ? `${groupOption.project.name} - ${groupOption.name}` : groupOption.name"
      :value="groupOption.id"
    >
      <div class="flex justify-between items-center">
        <ElTag v-if="groupOption.project">{{ groupOption.project?.name }}</ElTag>
        <ElSpace>
          {{ groupOption.name }}
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
