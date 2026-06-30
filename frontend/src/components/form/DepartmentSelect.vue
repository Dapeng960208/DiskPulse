<script setup>
import { ref, watch } from 'vue';
import { ElTreeSelect } from 'element-plus';
import departmentApi from '@/api/department-api';

const props = defineProps({
  modelValue: {
    type: Number,
    default: null,
  },
  checkStrictly: {
    type: Boolean,
    default: false,
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
const model = ref(props.modelValue || (props.multiple ? [] : null));
const departments = ref([]);

departmentApi.fetchTopLevel().then(({ result }) => {
  departments.value = result;
});

watch(model, (value) => emit('update:modelValue', value));
watch(() => props.modelValue, () => {
  model.value = props.modelValue || (props.multiple ? [] : null);
});
</script>

<template>
  <ElTreeSelect
    v-model="model"
    class="w-full"
    :data="departments"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :show-checkbox="multiple"
    :check-strictly="checkStrictly"
    node-key="id"
    :props="{
      label: 'name',
    }"
    :clearable="clearable"
  />
</template>
