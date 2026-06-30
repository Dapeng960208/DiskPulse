<script setup>
import { ref, onBeforeMount } from 'vue';
import { useRoute } from 'vue-router';
import RealTimePage from '@/pages/common/RealTimePage.vue';
const attributeId = ref(null);
const route = useRoute();

onBeforeMount(() => {
  attributeId.value = parseInt(route.params?.id);
});
</script>

<template>
  <RealTimePage
    :attribute-id="attributeId"
    :api-type="'project'"
    :label="'项目名'"></RealTimePage>
</template>
