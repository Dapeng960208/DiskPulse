<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace, ElTag } from 'element-plus';
import qtreeApi from '@/api/qtree-api';
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

const qtreeOptions = ref([]);
const queryParams = ref({
  page:1,size:20
});
const searchingQtree = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  qtreeOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((qtreeId) => {
    qtreeApi.fetchById(qtreeId).then((result) => {
      qtreeOptions.value.push(result);
    });
  });

  if (qtreeOptions.value.length === 0) {
    if (props.volumeId) {
      queryParams.value.volume_id = props.volumeId;
    }

    qtreeApi.fetch(queryParams.value).then((result) => {
      qtreeOptions.value = result.content;
    });
  }
}

function searchQtree(queryString) {
  if (queryString) {
    searchingQtree.value = true;
    if (props.volumeId) {
      queryParams.value.volume_id = props.volumeId;
    }
    queryParams.value.nameLike = queryString;
    qtreeApi.fetch(queryParams.value).then((result) => {
      qtreeOptions.value = result.content;
    }).finally(() => (searchingQtree.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingQtree"
    :remote-method="searchQtree"
    placeholder="根据Qtree模糊搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    :max-collapse-tags="10"
    :clearable="clearable"
    default-first-option
    filterable
    remote
    remote-show-suffix
    collapse-tags
    collapse-tags-tooltip
  >
    <ElOption
      v-for="qtreeOption of qtreeOptions"
      :key="qtreeOption.id"
      :label="qtreeOption.volume? `${qtreeOption.volume.name}/${qtreeOption.name}`:qtreeOption.name"
      :value="qtreeOption.id"
    >
      <div class="flex justify-between items-center">
        <ElTag v-if="qtreeOption.volume">{{ qtreeOption.volume?.name }}</ElTag>
        <ElSpace>
          {{ qtreeOption.name }}
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
