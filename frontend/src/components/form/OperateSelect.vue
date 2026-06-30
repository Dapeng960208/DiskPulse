<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect} from 'element-plus';

const props = defineProps({
  modelValue: {
    type: [Array,String],
    default: null,
  },
});
const emit = defineEmits(['update:modelValue']);
const model = ref(props.modelValue);
const operationOptions = ref([
  {
    label:'内存优化',
    value:'memory_optimize'
  },
  {
    label:'停止',
    value:'kill'
  },
  {
    label:'暂停',
    value:'stop'
  },
  {
    label:'恢复',
    value:'resume'
  }
  ]);
let shouldUpdateModel = true;
let shouldUpdateModelValue = true;


watch(model, (value) => {
  if (value == '') {
    value = null;
    model.value=null;
  }
  if (shouldUpdateModelValue) {
    shouldUpdateModel = false;
    emit('update:modelValue', value);
  } else {
    shouldUpdateModelValue = true;
  }
});
watch(() => props.modelValue, (value) => {
  if (value == '') {
    value = null;
    model.value=null;
  }
  if (shouldUpdateModel) {
    shouldUpdateModelValue = false;
    model.value = value;
  } else {
    shouldUpdateModel = true;
  }
});

</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    placeholder="选择操作类型"
    default-first-option
    filterable
    clearable
    collapse-tags
    collapse-tags-tooltip
  >
    <ElOption
      v-for=" operationOption,index in operationOptions"
      :key="index"
      :label="operationOption.label"
      :value="operationOption.value"
    >
    </ElOption>
  </ElSelect>
</template>
