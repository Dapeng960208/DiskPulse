<script setup>
import { computed } from 'vue';
import { ElDatePicker } from 'element-plus';
import { getShortcuts } from '@/utils/time-range';

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
  maxDays: {
    type: Number,
    default: undefined,
  },
});

const emit = defineEmits(['update:modelValue']);
const shortcuts = computed(() => getShortcuts(props.maxDays));
</script>

<template>
  <ElDatePicker
    :model-value="modelValue"
    type="datetimerange"
    range-separator="至"
    format="YYYY-MM-DD HH:mm:ss"
    value-format="YYYY-MM-DD HH:mm:ss"
    start-placeholder="开始日期时间"
    end-placeholder="结束日期时间"
    :shortcuts="shortcuts"
    @update:model-value="emit('update:modelValue', $event)" />
</template>
