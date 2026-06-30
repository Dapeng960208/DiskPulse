<script setup>
import { ElConfigProvider } from 'element-plus';
import zhCN from 'element-plus/dist/locale/zh-cn.min.mjs';
</script>

<template>
  <ElConfigProvider :locale="zhCN">
    <RouterView />
  </ElConfigProvider>
</template>
