<script setup>
import { ElMenuItem, ElSubMenu } from 'element-plus';

const props = defineProps({
  option: {
    type: Object,
    required: true,
  },
});

function shouldShowSection(option, index) {
  if (!option.section || !option.isVisible()) return false;
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    const previousOption = props.option.children[cursor];
    if (previousOption.isVisible()) {
      return previousOption.section !== option.section;
    }
  }
  return true;
}
</script>

<template>
  <template v-if="option.isVisible()">
    <template v-if="option.children?.length > 0">
      <!-- <RouteMenuItem v-if="option.children.length === 1 && option.hideOnSingleChild" :option="option.children[0]" /> -->
      <!-- 最多显示两级 -->
      <ElMenuItem
        v-if="option.children.length === 1 && option.hideOnSingleChild"
        :index="option.children[0].path">
        <i
          v-if="option.children[0].icon"
          :class="option.children[0].icon"
          class="flex-shrink-0 text-xl mr-1"></i>
        <template #title>
          {{ option.children[0].label }}
        </template>
      </ElMenuItem>
      <ElSubMenu
        v-else
        :index="option.index">
        <template #title>
          <i
            v-if="option.icon"
            :class="option.icon"
            class="flex-shrink-0 text-xl mr-1"></i>
          <span>{{ option.label }}</span>
        </template>
        <template
          v-for="(subOption, index) of option.children"
          :key="subOption.key">
          <li
            v-if="shouldShowSection(subOption, index)"
            class="route-menu-section"
            data-testid="menu-section"
            aria-hidden="true">
            {{ subOption.section }}
          </li>
          <RouteMenuItem :option="subOption" />
        </template>
      </ElSubMenu>
    </template>
    <ElMenuItem
      v-else
      :index="option.index">
      <i
        v-if="option.icon"
        :class="option.icon"
        class="flex-shrink-0 text-xl mr-1"></i>
      <template #title>
        {{ option.label }}
      </template>
    </ElMenuItem>
  </template>
</template>

<style scoped>
.route-menu-section {
  padding: var(--spacing-md) var(--spacing-xl) var(--spacing-xs);
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  line-height: var(--line-height-normal);
  user-select: none;
}
</style>
