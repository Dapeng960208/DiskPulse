<script setup>
import { ElDescriptionsItem } from 'element-plus';
import { onBeforeMount, ref } from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import { useRoute } from 'vue-router';
import { formatStorageTargetType } from '@/utils/storage-resource';
import groupApi from '@/api/group-api.js';
import { useBreadcrumbs } from '@/stores/breadcrumbs';
const route = useRoute();
const breadcrumbs = useBreadcrumbs();
const attributeId = ref(null);

async function loadProjectBreadcrumb() {
  try {
    const group = await groupApi.fetchById(attributeId.value);
    const projectName = group?.project?.name;
    const groupName = group?.name;
    breadcrumbs.setDetailBreadcrumb(
      route.name,
      projectName && groupName ? ['项目', projectName, `${groupName}项目组详情`] : [],
    );
  } catch {
    breadcrumbs.setDetailBreadcrumb(route.name, []);
  }
}

onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
  breadcrumbs.setDetailBreadcrumb(route.name, []);
  loadProjectBreadcrumb();
});

</script>

<template>
  <section class="detail-monitor-page">
    <RealTimePage
      class="detail-monitor-page__content"
      :attribute-id="attributeId"
      :api-type="'group'"
      :label="'项目组'"
      :show-header="false"
      :fill-content="true">
      <template #extra-descriptions="{ info }">
        <ElDescriptionsItem label="项目路径">{{ info?.linux_path }}</ElDescriptionsItem>
        <ElDescriptionsItem label="归属项目">{{ info?.project?.name }}</ElDescriptionsItem>
        <ElDescriptionsItem label="存储目标">{{ formatStorageTargetType(info?.storage_target?.type) }} / {{ info?.storage_target?.name || '-' }}</ElDescriptionsItem>
        <ElDescriptionsItem
          v-if="false"
          label="备份路径">{{ info?.back_path }}</ElDescriptionsItem>
      </template>
    </RealTimePage>
  </section>
</template>

<style scoped>
.detail-monitor-page {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.detail-monitor-page__content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}
</style>
