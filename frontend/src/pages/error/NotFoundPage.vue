<script setup>
import { ElButton } from 'element-plus';
import Result from '@/components/data/Result.vue';
</script>

<template>
  <Result
    title="404 Not Found"
    tip="抱歉，您访问的页面不存在"
    type="404">
    <ElButton
      type="primary"
      @click="() => $router.push('/')">
      返回首页
    </ElButton>
  </Result>
</template>
