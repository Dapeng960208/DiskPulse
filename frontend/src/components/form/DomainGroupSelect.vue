<script setup>
import { ElOption, ElSelect,ElSpace } from 'element-plus';
import { ref, watch } from 'vue';
import { useVModel } from '@vueuse/core';
import domainGroupApi from '@/api/domain-group-api';
const props = defineProps({
  modelValue: {
    type: [Number, Array],
    default: null,
  },
  type: {
    type: String,
    required: true,
    validator: (value) => ['distribution', 'security'].includes(value),
  },
  defaultOptions: {
    type: Array,
    default: null,
  },
  multiple: {
    type: Boolean,
    default: false,
  },
  multipleLimit: {
    type: Number,
    default: 0,
  },
  disabledGroupId: {
    type: Number,
    default: null,
  },
});
const emit = defineEmits(['update:modelValue']);
const model = useVModel(props, 'modelValue', emit);
const groupOptions = ref([]);
const searchingGroups = ref(false);

if (props.defaultOptions) {
  groupOptions.value = props.defaultOptions;
}

watch(() => props.multiple, (multiple) => {
  model.value = multiple ? [] : null;
});
watch(() => props.defaultOptions, (options) => {
  groupOptions.value = options;
});

function searchGroups(queryString) {
  if (queryString) {
    searchingGroups.value = true;

    domainGroupApi.fetch({
      nameLike: queryString,
      isEmailEnabled: props.type === 'distribution',
    }).then(({ result }) => {
      groupOptions.value = result.content;
    }).finally(() => (searchingGroups.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingGroups"
    :remote-method="searchGroups"
    placeholder="根据名称搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    clearable
    default-first-option
    filterable
    remote
    remote-show-suffix
  >
    <ElOption
      v-for="groupOption of groupOptions"
      :key="groupOption.id"
      :label="groupOption.emailAddress"
      :value="groupOption.emailAddress"
      :disabled="groupOption.id === disabledGroupId"
    >
      <ElSpace>
        {{ groupOption.name }}({{ groupOption.emailAddress }})
      </ElSpace>
    </ElOption>
  </ElSelect>
</template>
