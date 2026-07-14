<script setup>
import { ElRow,ElCol,ElDescriptionsItem } from 'element-plus';
import { ref,onBeforeMount} from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import { useRoute } from 'vue-router';
import { formatStorageTargetType } from '@/utils/storage-resource';
const route = useRoute();
const attributeId = ref(null);
onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
});

</script>

<template>
  <RealTimePage
    :attribute-id="attributeId"
    :api-type="'group'"
    :label="'项目组'">
    <template #extra-descriptions="{ info }">
      <ElDescriptionsItem label="项目路径">{{ info?.linux_path }}</ElDescriptionsItem>
      <ElDescriptionsItem label="归属项目">{{ info?.project?.name }}</ElDescriptionsItem>
      <ElDescriptionsItem label="存储目标">
        {{ formatStorageTargetType(info?.storage_target?.type) }} / {{ info?.storage_target?.name || '-' }}
      </ElDescriptionsItem>
      <ElDescriptionsItem
        v-if="false"
        label="备份路径">{{ info?.back_path }}</ElDescriptionsItem>
    </template>
  </RealTimePage>

</template>
