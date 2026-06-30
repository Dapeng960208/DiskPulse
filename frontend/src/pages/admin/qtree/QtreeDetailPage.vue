<script setup>
import { ElRow,ElCol } from 'element-plus';
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
    :api-type="'qtree'"
    :label="'Qtree名'"></RealTimePage>
</template>
