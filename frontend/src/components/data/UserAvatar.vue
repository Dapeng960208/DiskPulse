<script setup>
import { ElAvatar } from 'element-plus';

defineProps({
  src: {
    type: String,
    default: undefined,
  },
  size: {
    type: [Number, String],
    validator(value) {
      return typeof value === 'number' || ['large', 'default', 'small'].includes(value);
    },
    default: 'default',
  },
});
</script>

<template>
  <ElAvatar
    :src="src"
    :size="size"
    class="user-avatar">
    <ICarbonUserFilled class="default-avatar-icon" />
  </ElAvatar>
</template>

<style lang="scss" scoped>
.user-avatar {
  background: var(--primary-gradient);
  color: white;
  border: 2px solid var(--border-light);
  transition: var(--transition-base);

  &:hover {
    border-color: var(--primary-color);
    transform: scale(1.05);
  }

  .default-avatar-icon {
    font-size: 1.2em;
    opacity: 0.9;
  }
}
</style>
