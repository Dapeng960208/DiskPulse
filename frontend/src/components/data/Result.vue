<script setup lang="ts">
import { computed } from 'vue';
import Result403Icon from '@/assets/assets-result-403.svg';
import Result404Icon from '@/assets/assets-result-404.svg';
import Result500Icon from '@/assets/assets-result-500.svg';
import ResultIeIcon from '@/assets/assets-result-ie.svg';
import ResultMaintenanceIcon from '@/assets/assets-result-maintenance.svg';
import ResultWifiIcon from '@/assets/assets-result-wifi.svg';

const props = defineProps({
  bgUrl: String,
  title: String,
  tip: String,
  type: String,
});

const iconUrl = computed(() => {
  switch (props.type) {
    case '403':
      return Result403Icon;
    case '404':
      return Result404Icon;
    case '500':
      return Result500Icon;
    case 'ie':
      return ResultIeIcon;
    case 'wifi':
      return ResultWifiIcon;
    case 'maintenance':
      return ResultMaintenanceIcon;
    default:
      return Result403Icon;
  }
});
</script>

<template>
  <div class="h-full flex flex-col justify-center items-center">
    <div class="w-200px">
      <img :src="iconUrl">
    </div>
    <div class="my-4 text-2xl font-bold">
      {{ title }}
    </div>
    <div class="mb-8 text-true-gray-500">
      {{ tip }}
    </div>
    <slot></slot>
  </div>
</template>
