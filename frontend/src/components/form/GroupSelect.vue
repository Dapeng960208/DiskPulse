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
  groupTagId: {
    type: Number,
    default: null,
  }
});
const emit = defineEmits(['update:modelValue', 'selected-label-change']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const groupOptions = ref([]);
const queryParams = ref({
  page:1,size:20
});
const searchingUserGroups = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });
watch(
  () => [props.projectId, props.groupTagId],
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
  if (props.groupTagId) {
    queryParams.value.group_tag_id = props.groupTagId;
  } else {
    delete queryParams.value.group_tag_id;
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

function emitSelectedLabel(value) {
  const labels = toSelectValues(value, props.multiple).map((id) => {
    const option = groupOptions.value.find((item) => item.id === id);
    return option?.project ? `${option.project.name} - ${option.name}` : option?.name;
  }).filter(Boolean);
  emit('selected-label-change', labels.length ? labels.join('、') : null);
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
    @change="emitSelectedLabel"
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
