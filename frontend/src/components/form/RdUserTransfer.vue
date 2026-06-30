<script setup>
import { ref, watch,onBeforeMount } from 'vue';
import { ElTransfer,ElTag } from 'element-plus';
import rdUsersApi from '@/api/users-api.js';

const props = defineProps({
  modelValue: {
    type: Array,
    default: [],
  },
  returnField: {
    type: String,
    default: 'id',
  },
});

const emit = defineEmits(['update:modelValue']);
const model = ref(props.modelValue);
const userOptions = ref([]);
const selectedField = ref(props.returnField); // 新增字段来维护返回的字段
const searchingUsers = ref(true); // 初始值为 true
let shouldUpdateModel = true;
let shouldUpdateModelValue = true;

// 监听 model 的变化
watch(model, (value) => {
  if (shouldUpdateModelValue) {
    shouldUpdateModel = false;
    const returnValue = Array.isArray(value)
      ? value.map((v) => getOptionField(v))
      : getOptionField(value);
    emit('update:modelValue', returnValue);
  } else {
    shouldUpdateModelValue = true;
  }
});

// 监听 props.modelValue 的变化
watch(() => props.modelValue, (value) => {
  if (value === '') {
    value = null;
    model.value = null;
  }
  if (shouldUpdateModel) {
    shouldUpdateModelValue = false;
    model.value = value;
    initDefaultOptions();
  } else {
    shouldUpdateModel = true;
  }
});

// 初始化默认选项
function initDefaultOptions() {
  searchingUsers.value = true;
  rdUsersApi.fetch({ page: 1, size: 10000,load_detail:false }).then((result) => {
    userOptions.value = result.content.map((user) => ({
      ...user,
      disabled: false,
    }));
    searchingUsers.value = false;
  });
}

function getOptionField(value) {
  const option = userOptions.value.find((opt) => opt.id === value);
  return option ? option[selectedField.value] : value;
}

// 在组件挂载前初始化默认选项
onBeforeMount(() => {
  initDefaultOptions();
});
</script>

<template>
  <div
    v-if="!searchingUsers"
    class="transfer-container">
    <ElTransfer
      v-model="model"
      :data="userOptions"
      filterable
      :titles="['可选用户', '已选用户']"
      :props="{ key: 'id', label: 'rd_username' }"
    >
      <template #default="{ option }">
        <span>{{ option.rd_username }}</span>
        <ElTag v-if="option.department">
          {{ option.department }}
        </ElTag>
      </template>
    </ElTransfer>
  </div>
</template>

<style scoped>
:deep(.el-transfer-panel) {
  width: 400px; /* Set the width of the el-transfer-panel to 300px */
}

.ml-2 {
  margin-left: 1rem;
}
</style>
