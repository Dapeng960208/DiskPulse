<script setup>
import { computed, ref, watch } from 'vue';
import capacityPredictionApi from '@/api/capacity-prediction-api.js';

const props = defineProps({
  assetType: { type: String, required: true },
  assetId: { type: Number, required: true },
});

const risk = ref(null);
const loading = ref(false);
const error = ref('');
const loaded = ref(false);

const tagType = computed(() => ({
  critical: 'danger',
  high: 'warning',
  watch: 'warning',
  none: 'success',
  insufficient: 'info',
}[risk.value?.level] || 'info'));

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  const pad = (part) => String(part).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

const expectedExhaustion = computed(() => {
  if (!risk.value) return '-';
  if (risk.value.p50_exhaustion_at) return `P50：${formatDate(risk.value.p50_exhaustion_at)}`;
  if (risk.value.p90_exhaustion_at) return `P90：${formatDate(risk.value.p90_exhaustion_at)}`;
  return risk.value.level === 'none' ? '未来 30 日内不会触碰硬限额' : '-';
});

async function load() {
  if (!Number.isInteger(props.assetId) || props.assetId < 1) return;
  loading.value = true;
  error.value = '';
  loaded.value = false;
  try {
    risk.value = await capacityPredictionApi.fetchRisk(props.assetType, props.assetId, {
      errorHandlerDisabled: true,
    });
  } catch (requestError) {
    risk.value = null;
    if (requestError?.response?.status !== 404) {
      error.value = requestError?.response?.status === 403
        ? '当前账号无权查看耗尽风险'
        : '加载耗尽风险失败，请稍后重试';
    }
  } finally {
    loaded.value = true;
    loading.value = false;
  }
}

watch(() => [props.assetType, props.assetId], load, { immediate: true });
</script>

<template>
  <section
    v-loading="loading"
    class="capacity-exhaustion-risk-panel">
    <div
      v-if="error"
      class="capacity-exhaustion-risk-panel__error"
      role="alert">{{ error }}</div>
    <div
      v-else-if="loaded && !risk"
      class="capacity-exhaustion-risk-panel__empty">暂无耗尽风险结果</div>
    <dl
      v-else-if="risk"
      class="capacity-exhaustion-risk-panel__summary">
      <div>
        <dt>耗尽风险</dt>
        <dd><span :class="['capacity-exhaustion-risk-panel__tag', `is-${tagType}`]">{{ risk.label }}</span></dd>
      </div>
      <div>
        <dt>预计耗尽</dt>
        <dd>{{ expectedExhaustion }}</dd>
      </div>
      <div>
        <dt>判断依据</dt>
        <dd>{{ risk.reason }}</dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.capacity-exhaustion-risk-panel { min-height: 120px; }
.capacity-exhaustion-risk-panel__summary { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.capacity-exhaustion-risk-panel__summary > div { padding: var(--spacing-md); }
.capacity-exhaustion-risk-panel__summary > div + div { border-left: 1px solid var(--border-color); }
.capacity-exhaustion-risk-panel__summary dt { color: var(--text-secondary); }
.capacity-exhaustion-risk-panel__summary dd { margin: var(--spacing-sm) 0 0; color: var(--text-primary); }
.capacity-exhaustion-risk-panel__tag { display: inline-flex; padding: 2px 9px; border-radius: 999px; background: var(--bg-secondary); }
.capacity-exhaustion-risk-panel__tag.is-danger { color: var(--danger-color); }
.capacity-exhaustion-risk-panel__tag.is-warning { color: var(--warning-color); }
.capacity-exhaustion-risk-panel__tag.is-success { color: var(--success-color); }
.capacity-exhaustion-risk-panel__error { color: var(--danger-color); }
.capacity-exhaustion-risk-panel__empty { color: var(--text-secondary); text-align: center; padding: var(--spacing-xl); }

@media (max-width: 900px) {
  .capacity-exhaustion-risk-panel__summary { grid-template-columns: 1fr; }
  .capacity-exhaustion-risk-panel__summary > div + div { border-top: 1px solid var(--border-color); border-left: 0; }
}
</style>
