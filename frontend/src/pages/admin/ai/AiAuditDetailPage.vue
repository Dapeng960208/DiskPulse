<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElButton, ElDescriptions, ElDescriptionsItem, ElTag } from 'element-plus';
import aiApi from '@/api/ai-api';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

const route = useRoute();
const router = useRouter();
const breadcrumbs = useBreadcrumbs();
const audit = ref(null);

onMounted(async () => {
  breadcrumbs.setDetailTitle(route.name, '');
  try {
    audit.value = await aiApi.getAudit(route.params.id);
    breadcrumbs.setDetailTitle(route.name, `审计记录 #${route.params.id}`);
  } catch {
    audit.value = null;
  }
});
</script>

<template>
  <section class="audit-detail">
    <div class="heading"><div><h2>审计记录 #{{ route.params.id }}</h2><p>请求与响应仅保留脱敏摘要，工具结果不在此展示。</p></div><ElButton @click="router.push('/admin/ai-center?tab=audit')">返回审计</ElButton></div>
    <ElDescriptions
      v-if="audit"
      :column="2"
      border>
      <ElDescriptionsItem label="状态"><ElTag>{{ audit.status }}</ElTag></ElDescriptionsItem>
      <ElDescriptionsItem label="Trace ID">{{ audit.trace_id }}</ElDescriptionsItem>
      <ElDescriptionsItem label="用户">{{ audit.user_id }}</ElDescriptionsItem>
      <ElDescriptionsItem label="模型">{{ audit.model_id }}</ElDescriptionsItem>
      <ElDescriptionsItem label="会话">{{ audit.conversation_id }}</ElDescriptionsItem>
      <ElDescriptionsItem label="工具调用">{{ audit.tool_call_count }}（失败 {{ audit.tool_failed_count }}）</ElDescriptionsItem>
      <ElDescriptionsItem label="开始时间">{{ audit.started_at }}</ElDescriptionsItem>
      <ElDescriptionsItem label="结束时间">{{ audit.finished_at || '-' }}</ElDescriptionsItem>
      <ElDescriptionsItem
        label="请求摘要"
        :span="2"><pre>{{ JSON.stringify(audit.request, null, 2) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem
        label="响应摘要"
        :span="2"><pre>{{ JSON.stringify(audit.response, null, 2) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem
        label="工具轨迹"
        :span="2"><pre>{{ JSON.stringify(audit.detail, null, 2) }}</pre></ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="audit.error_message"
        label="错误"
        :span="2">{{ audit.error_message }}</ElDescriptionsItem>
    </ElDescriptions>
  </section>
</template>

<style scoped>
.heading { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 18px; }
h2 { margin: 0 0 5px; font-size: 22px; }
p { margin: 0; color: var(--text-secondary); }
pre { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; }
</style>
