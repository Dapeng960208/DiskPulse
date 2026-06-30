<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace } from 'element-plus';
import storageUsageApi from '@/api/storage-usage-api';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [Number, Array],
    default: null,
  },
  multiple: {
    type: Boolean,
    default: false,
  },
  multipleLimit: {
    type: Number,
    default: null,
  },
  clearable: {
    type: Boolean,
    default: false,
  },
  volumeId:{
    type:Number,
    default:null
  }
});
const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const storageUsageOptions = ref([]);
const queryParams = ref({
  page:1,size:20
});
const searchingStorageUsage = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  storageUsageOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((storageUsageId) => {
    storageUsageApi.fetchById(storageUsageId).then((result) => {
      storageUsageOptions.value.push(result);
    });
  });

  if (storageUsageOptions.value.length === 0) {
    if (props.volumeId) {
      queryParams.value.volume_id = props.volumeId;
    }

    storageUsageApi.fetch(queryParams.value).then((result) => {
      storageUsageOptions.value = result.content;
    });
  }
}

function searchStorageUsage(queryString) {
  if (queryString) {
    searchingStorageUsage.value = true;
    if (props.volumeId) {
      queryParams.value.volume_id = props.volumeId;
    }
    queryParams.value.nameLike = queryString;
    storageUsageApi.fetch(queryParams.value).then((result) => {
      storageUsageOptions.value = result.content;
    }).finally(() => (searchingStorageUsage.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingStorageUsage"
    :remote-method="searchStorageUsage"
    placeholder="根据StorageUsage模糊搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    :max-collapse-tags="10"
    :clearable="clearable"
    default-first-option
    filterable
    remote
    remote-show-suffix
    :collapse-tags="true"
    :collapse-tags-tooltip="true"
  >
    <ElOption
      v-for="storageUsageOption of storageUsageOptions"
      :key="storageUsageOption.id"
      :label="storageUsageOption.linux_path"
      :value="storageUsageOption.id"
    >
      <div class="flex justify-between items-center">
        <ElSpace>
          {{ storageUsageOption.linux_path }}
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
