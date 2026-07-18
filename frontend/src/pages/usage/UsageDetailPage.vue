<script setup>
// 暂时隐藏第 2–4 行扩展字段，恢复时取消以下导入与模板注释。
// import { ElDescriptionsItem } from 'element-plus';
import { defineAsyncComponent, onBeforeMount, ref } from 'vue';
import { ElButton } from 'element-plus';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';
import { useRoute } from 'vue-router';
const route = useRoute();
const attributeId = ref(null);
const predictionVisible = ref(false);
const canManagePlans = ref(false);
const activeView = ref('realtime');
const CapacityPredictionPanel = defineAsyncComponent(() => import('@/pages/capacity-prediction/CapacityPredictionPanel.vue'));
onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
  capacityPredictionApi.access('storage_usage', attributeId.value).then((value) => {
    predictionVisible.value = value.visible === true;
    canManagePlans.value = value.can_manage_plans === true;
  }).catch(() => { predictionVisible.value = false; canManagePlans.value = false; });
});

</script>

<template>
  <section class="detail-monitor-page">
    <template v-if="activeView === 'realtime'">
      <div class="flex justify-end mb-4">
        <ElButton
          v-if="predictionVisible"
          data-testid="capacity-prediction-entry"
          type="primary"
          @click="activeView = 'prediction'">容量预测</ElButton>
      </div>
      <RealTimePage
        :attribute-id="attributeId"
        :api-type="'storage-usage'"
        :label="'研发用户目录'"
        :show-header="false">
        <!-- 暂时隐藏第 2–4 行扩展字段
        <template #extra-descriptions="{ info }">
          <ElDescriptionsItem label="文件数量">{{ info?.file_used }}</ElDescriptionsItem>
          <ElDescriptionsItem label="目录权限">{{ info?.access }}</ElDescriptionsItem>
          <ElDescriptionsItem label="访问时间(Access Time)">{{ info?.access_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="修改时间(Modify Time)">{{ info?.modify_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="改变时间(Change Time)">{{ info?.change_time }}</ElDescriptionsItem>
          <ElDescriptionsItem label="创建时间">{{ info?.resources_content }}</ElDescriptionsItem>
          <ElDescriptionsItem label="权限组">{{ info?.gid }}</ElDescriptionsItem>
          <ElDescriptionsItem label="Inode编号">{{ info?.inode }}</ElDescriptionsItem>
          <ElDescriptionsItem label="硬链接数量">{{ info?.links }}</ElDescriptionsItem>
          <ElDescriptionsItem label="系统的I/O块大小">{{ info?.blocks }}</ElDescriptionsItem>
          <ElDescriptionsItem label="IO块(IO Block)">{{ info?.io_block }}</ElDescriptionsItem>
          <ElDescriptionsItem label="设备的标识号">{{ info?.device }}</ElDescriptionsItem>
        </template>
        -->
      </RealTimePage>
    </template>
    <template v-else>
      <div class="mb-4">
        <ElButton @click="activeView = 'realtime'">返回实时监控</ElButton>
      </div>
      <CapacityPredictionPanel
        asset-type="storage_usage"
        :asset-id="attributeId"
        :visible="predictionVisible"
        :can-manage-plans="canManagePlans" />
    </template>
  </section>
</template>
