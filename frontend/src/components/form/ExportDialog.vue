<script setup>
import { ElButton, ElForm, ElFormItem, ElOption, ElSelect, ElDialog } from 'element-plus';
import { ref } from 'vue';

const emit = defineEmits(['submitted']);

const exportOptions = [
  { label: '报表(xlsx)', value: 'excel' },
  { label: '报告(pdf)', value: 'pdf' }
];

const visible = ref(false);
const model = ref({ export_type: 'pdf' });

const open = () => {
  visible.value = true;
};

const close = () => {
  visible.value = false;
};

const submit = () => {
  if (model.value.export_type) {
    emit('submitted', model.value.export_type);
    close();
  }
};

defineExpose({
  open
});
</script>

<template>
  <ElDialog
    v-model="visible"
    title="数据导出"
    @close="close">
    <ElForm
      label-width="auto"
      :model="model"
      align="center">
      <ElFormItem
        label="导出类型"
        prop="export_type">
        <ElSelect
          v-model="model.export_type"
          placeholder="选择导出类型"
          style="width:100%"
        >
          <ElOption
            v-for="item in exportOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </ElSelect>
      </ElFormItem>
    </ElForm>
    <template #footer>
      <ElButton @click="close">
        取消
      </ElButton>
      <ElButton
        type="primary"
        @click="submit">
        确认导出
      </ElButton>
    </template>
  </ElDialog>
</template>
