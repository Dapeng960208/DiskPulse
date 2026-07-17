<script setup>
import { ElProgress } from 'element-plus';
import { getQuotaProgressColor } from '@/utils/storage-alert-rule';
import { useStorageAlertThresholds } from '@/stores/storage-alert-thresholds';

const alertThresholds = useStorageAlertThresholds();
alertThresholds.load();

const props = defineProps({
  used: {
    type: [Number, null],
    required: true,
  },
  total: {
    type: [Number, null],
    required: true,
  },
  showNumbers: {
    type: Boolean,
    default: true,
  },
});

function calculatePercentage(value, total) {
  if (value === null || total === null || total === 0) {
    return 0;
  }

  const percentage = (value / total) * 100;
  return Math.min(Math.max(parseFloat(percentage.toFixed(2)), 0), 100);
}

function getColor(percentage) {
  return getQuotaProgressColor(percentage, alertThresholds.thresholds);
}
</script>

<template>
  <div
    v-if="props.total >= 0 && props.used >= 0"
    class="progress-wrapper">
    <ElProgress
      class="progress-bar"
      :text-inside="true"
      :stroke-width="18"
      striped
      :percentage="calculatePercentage(props.used, props.total)"
      :color="getColor"
      :style="{ width: props.showNumbers ? '70%' : '100%' }"
    />
    <div
      v-if="props.showNumbers"
      class="progress-numbers">
      {{ props.used?.toFixed(0) }} / {{ props.total?.toFixed(0) }}
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.progress-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;

  .progress-bar {
    :deep(.el-progress-bar__outer) {
      border-radius: 9999px;
      background: var(--bg-tertiary);
    }

    :deep(.el-progress-bar__inner) {
      border-radius: 9999px;
      transition: width 0.6s ease;
    }

    :deep(.el-progress-bar__innerText) {
      font-size: 11px;
      font-weight: 600;
    }
  }

  .progress-numbers {
    width: 30%;
    text-align: center;
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    font-weight: var(--font-weight-medium);
    white-space: nowrap;
  }
}
</style>
