<script setup>
import { ElLink } from 'element-plus';
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { canAccessRoute } from '@/router/support/accessibility';

defineOptions({ inheritAttrs: false });

const props = defineProps({
  to: {
    type: Object,
    default: null,
  },
});

const router = useRouter();
const isAccessible = computed(() => canAccessRoute(router, props.to));

function navigate() {
  if (isAccessible.value) router.push(props.to);
}
</script>

<template>
  <ElLink
    v-if="isAccessible"
    class="accessible-resource-link__link"
    v-bind="$attrs"
    :underline="false"
    @click="navigate">
    <slot></slot>
  </ElLink>
  <span
    v-else
    class="accessible-resource-link__text">
    <slot></slot>
  </span>
</template>

<style scoped>
:deep(.accessible-resource-link__link) {
  --el-link-text-color: #5b84ad;
  --el-link-hover-text-color: #4d759d;
  color: #5b84ad;
  font-size: inherit;
  font-weight: 400;
}

:deep(.accessible-resource-link__link:hover),
:deep(.accessible-resource-link__link:focus-visible) {
  color: #4d759d;
}
</style>
