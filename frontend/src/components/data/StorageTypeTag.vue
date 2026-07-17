<script setup>
import { ElTag } from 'element-plus';

defineProps({
  value: {
    type: String,
    default: null,
  },
});
</script>

<template>
  <ElTag
    v-if="value"
    type="success">{{ value }}</ElTag>
  <span v-else>-</span>
</template>
