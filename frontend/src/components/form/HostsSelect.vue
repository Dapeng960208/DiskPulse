<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace } from 'element-plus';
import hostApi from '@/api/host-api.js';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [Number, Array, String],
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
  initOption: {
    type: Array,
    default: [],
  },
  returnField: {
    type: String,
    default: 'id',
  },
});

const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit, {
  transformOutput: (value) => (
    props.multiple
      ? (value ?? []).map((item) => getOptionField(item))
      : getOptionField(value)
  ),
});
const hostOptions = ref([]);
const searchingHosts = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  hostOptions.value = [];

  if (props.multiple) {
    if (props.initOption.length > 0) {
      hostOptions.value = [...props.initOption];
    } else {
      toSelectValues(selectedValue, true).forEach((hostId) => {
        hostApi.fetchById(hostId).then((result) => {
          hostOptions.value.push(result);
        });
      });
    }
  } else if (selectedValue != null) {
    hostApi.fetchById(selectedValue).then((result) => {
      hostOptions.value.push(result);
    });
  }

  if (hostOptions.value.length === 0) {
    hostApi.fetch({ page: 1, size: 20 }).then((result) => {
      hostOptions.value = result.content;
    });
  }
}

// 搜索主机
function searchHosts(queryString) {
  if (queryString) {
    searchingHosts.value = true;
    hostApi.fetch({ nameLike: queryString }).then(({ content }) => {
      hostOptions.value = content;
    }).finally(() => {
      searchingHosts.value = false;
    });
  }
}

// 获取选项字段
function getOptionField(value) {
  const option = hostOptions.value.find((opt) => opt.id === value);
  return option ? option[props.returnField] : value;
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingHosts"
    :remote-method="searchHosts"
    placeholder="根据主机名搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    :max-collapse-tags="10"
    :clearable="clearable"
    value-key="id"
    default-first-option
    filterable
    remote
    remote-show-suffix
    collapse-tags
    collapse-tags-tooltip
  >
    <ElOption
      v-for="hostOption of hostOptions"
      :key="hostOption.id"
      :label="hostOption.name"
      :value="hostOption.id"
    >
      <div class="flex justify-between items-center">
        <ElSpace>
          {{ hostOption.name }}
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
