<script setup>
import { ElMenuItem, ElSubMenu } from 'element-plus';

defineProps({
  option: {
    type: Object,
    required: true,
  },
});
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
        <RouteMenuItem
          v-for="subOption of option.children"
          :key="subOption.key"
          :option="subOption" />
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
