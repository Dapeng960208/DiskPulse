<script setup>
import RealTimePage from '@/pages/common/RealTimePage.vue';

defineProps({
  attributeId: {
    type: Number,
    default: null,
  },
});
</script>

<template>
  <RealTimePage
    :attribute-id="attributeId"
    api-type="project"
    label="项目"
    :show-header="false"
    :show-resource-select="!attributeId"
    :allowed-indicators="['used']"
    :fill-content="Boolean(attributeId)" />
</template>
