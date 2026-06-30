<script setup>
import { ElButton } from 'element-plus';
import Result from '@/components/data/Result.vue';
</script>

<template>
  <Result
    title="403 Unauthorized"
    tip="抱歉，您暂无权限访问本页面"
    type="403">
    <ElButton
      type="primary"
      @click="() => $router.push('/')">
      返回首页
    </ElButton>
  </Result>
</template>
