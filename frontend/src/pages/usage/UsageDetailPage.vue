<script setup>
import { ElRow,ElCol,ElDescriptionsItem } from 'element-plus';
import { ref,onBeforeMount} from 'vue';
import RealTimePage from '@/pages/common/RealTimePage.vue';
import { useRoute } from 'vue-router';
const route = useRoute();
const attributeId = ref(null);
onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
});

</script>

<template>
  <RealTimePage
    :attribute-id="attributeId"
    :api-type="'storage-usage'"
    :label="'研发用户目录'">
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
  </RealTimePage>

</template>
