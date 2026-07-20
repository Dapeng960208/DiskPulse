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
  <section class="project-disk-usage">
    <RealTimePage
      class="project-disk-usage__content"
      :attribute-id="attributeId"
      api-type="project"
      label="项目"
      :show-header="false"
      :show-resource-select="!attributeId"
      :allowed-indicators="['used']"
      :fill-content="Boolean(attributeId)" />
  </section>
</template>

<style scoped>
.project-disk-usage {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.project-disk-usage__content {
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
}
</style>
