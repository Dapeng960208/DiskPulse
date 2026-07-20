<script setup>
import RealTimePage from '@/pages/common/RealTimePage.vue';

defineProps({
  attributeId: {
    type: Number,
    required: true,
  },
});
</script>

<template>
  <RealTimePage
    :attribute-id="attributeId"
    api-type="project"
    label="项目"
    :show-header="false"
    :show-resource-select="false"
    :allowed-indicators="['used']" />
</template>
