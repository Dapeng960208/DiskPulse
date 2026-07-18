<script setup>
import { ElButton } from 'element-plus';
import { computed } from 'vue';

defineOptions({ inheritAttrs: false });

const props = defineProps({
  action: {
    type: String,
    required: true,
  },
});

const actionTypes = Object.freeze({
  create: 'success',
  detail: 'info',
  edit: 'primary',
  delete: 'danger',
  remove: 'danger',
  activate: 'success',
  sync: 'success',
  rollback: 'success',
  test: 'primary',
});

const type = computed(() => actionTypes[props.action] || 'primary');
</script>

<template>
  <ElButton
    v-bind="$attrs"
    :type="type"
    size="small"
    plain>
    <slot></slot>
  </ElButton>
</template>
