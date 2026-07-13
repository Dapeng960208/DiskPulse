<script setup>
import { defineAsyncComponent, ref, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import RealTimePage from '@/pages/common/RealTimePage.vue';
const ProjectStorageEnvironmentTable = defineAsyncComponent(
  () => import('./components/ProjectStorageEnvironmentTable.vue'),
);
const attributeId = ref(null);
const route = useRoute();

onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
});
</script>

<template>
  <div class="project-detail-page">
    <RealTimePage
      :attribute-id="attributeId"
      :api-type="'project'"
      :label="'项目名'"></RealTimePage>

    <section class="mt-5">
      <h2 class="mb-3 text-lg font-semibold">
        存储环境
      </h2>
      <ProjectStorageEnvironmentTable
        v-if="attributeId"
        :project-id="attributeId" />
    </section>
  </div>
</template>
