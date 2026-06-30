<script setup>
import { ElLink } from 'element-plus';

defineProps({
  to: {
    type: String,
    required: true,
  },
  type: {
    type: String,
    validator: (value) => ['primary', 'success', 'warning', 'danger', 'info', 'default'].includes(value),
    default: 'default',
  },
  external: {
    type: Boolean,
    default: false,
  },
  underline: {
    type: Boolean,
    default: true,
  },
  disabled: {
    type: Boolean,
    default: undefined,
  },
  target: {
    type: String,
    default: '',
  },
});
</script>

<template>
  <ElLink
    v-if="external"
    :type="type"
    :href="to"
    :underline="underline"
    :disabled="disabled"
    :target="target"
  >
    <slot></slot>
  </ElLink>
  <RouterLink
    v-else
    v-slot="{ href, navigate }"
    :to="to"
    custom
  >
    <ElLink
      :type="type"
      :href="href"
      :underline="underline"
      :disabled="disabled"
      :target="target"
      @click="navigate"
    >
      <slot></slot>
    </ElLink>
  </RouterLink>
</template>
