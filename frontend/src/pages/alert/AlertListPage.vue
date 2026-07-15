<script setup>
import { ref } from 'vue';
import { ElFormItem, ElInput, ElTableColumn, ElOption, ElSelect, ElTag } from 'element-plus';
import alertApi from '@/api/alert-api.js';
import FilterForm from '@/components/form/QueryForm.vue';
import DataTable from '@/components/data/DataTable.vue';
import { useQuery, useQueryParams } from '@/composables/query';

const { queryParams, reset } = useQueryParams(() => ({
  page: 1,
  size: 20,
  alert_type: '',
  prop:null,
  order:null

}));

const alertOptions = {
  '用户目录': 'StorageUsage',
  '项目组': 'Group',
  '项目': 'Project',
  '容量池': 'Aggregate',
  '存储空间': 'Volume',
  'Qtree（NetApp）': 'Qtree',
};

const handleRelatedTypeChange = (value) => {
  queryParams.value.related_type = value;
  queryParams.value.related_id = null;
};

const handleReset = () => {
  reset();
  query();
};

const alertTypeOptions = [
  { value: 'alert', label: '告警' },
  { value: 'report', label: '周报' },
  { value: 'expand', label: '扩容' },
];

const alertTypeDisplay = (alertType) => {
  switch (alertType) {
    case 'alert':
      return '告警';
    case 'report':
      return '周报';
    case 'expand':
      return '扩容';
    case 'vendor_event':
      return '系统事件';
    default:
      return '-';
  }
};

const alertLevelDisplay = (alertLevel) => {
  switch (alertLevel) {
    case 'high':
      return 'danger';
    case 'medium':
      return 'warning';
    default:
      return 'success';
  }
};

const { result, querying, query } = useQuery(() => alertApi.fetch(queryParams.value), {
  content: [],
  totalElements: 0,
});

query();
</script>

<template>
  <div class="user-list-page">
    <FilterForm
      @query="{
        queryParams.page = 1;
        query();
      }"
      @reset="handleReset"
    >
      <ElFormItem
        label="关键词"
        class="query-form-field--wide">
        <ElInput
          v-model="queryParams.nameLike"
          placeholder="根据关键词模糊搜索" />
      </ElFormItem>
      <ElFormItem label="类型">
        <ElSelect
          v-model="queryParams.alert_type"
          placeholder="请选择类型"
        >
          <ElOption
            v-for="option in alertTypeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="分类">
        <ElSelect
          :model-value="queryParams.related_type"
          placeholder="请选择分类"
          @update:model-value="handleRelatedTypeChange"
        >
          <ElOption
            v-for="(value, key) in alertOptions"
            :key="key"
            :label="key"
            :value="value"
          />
        </ElSelect>
      </ElFormItem>
    </FilterForm>

    <DataTable
      :pagination="{
        page: queryParams.page,
        pageSize: queryParams.size,
        total: result.total,
        pageSizes: [20, 50, 100, 200, 500],
        hideOnSinglePage: true,
        showJumper: true,
      }"
      :loading="querying"
      :data="result.content"
      @update:pagination="({ page, pageSize, prop, order }) => {
        queryParams.page = page;
        queryParams.size = pageSize;
        queryParams.prop = prop;
        queryParams.order = order;
        query();
      }"
    >
      <ElTableColumn
        label="类型"
        align="center"
        prop="alert_type"
        min-width="60"
      >
        <template #default="{ row }">
          <ElTag :type="alertTypeDisplay(row.alert_type) === '告警' ? 'danger' : alertTypeDisplay(row.alert_type) === '周报' ? 'success' : 'warning'">
            {{ alertTypeDisplay(row.alert_type) }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目"
        align="center"
        min-width="80">
        <template #default="{ row }">
          <span v-if="row.related_type === 'Group'">
            {{ row.related_info?.project?.name || '-' }}
          </span>
          <span v-else>-</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="项目组标签"
        align="center"
        min-width="80">
        <template #default="{ row }">
          <span v-if="row.related_type === 'Group'">
            {{ row.related_info?.group_tag?.name || '-' }}
          </span>
          <span v-else>-</span>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="内容"
        align="center"
        prop="description"
        min-width="300"
      />
      <ElTableColumn
        label="级别"
        align="center"
        prop="alert_level"
        min-width="60"
      >
        <template #default="{ row }">
          <ElTag :type="alertLevelDisplay(row.alert_level)">
            {{ row.alert_level }}
          </ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn
        label="阈值"
        align="center"
        sortable
        prop="threshold"
        min-width="60"
      />
      <ElTableColumn
        label="触发值"
        align="center"
        sortable
        prop="avg_use_ratio"
        min-width="60"
      />
      <ElTableColumn
        label="时间"
        align="center"
        sortable
        prop="updated_at"
        min-width="100"
      />
    </DataTable>
  </div>
</template>
