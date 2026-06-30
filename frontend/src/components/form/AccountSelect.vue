<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace } from 'element-plus';
import accountApi from '@/api/account-api';
import UserAvatar from '@/components/data/UserAvatar.vue';
import { toSelectValues, useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [Number, Array],
    default: null,
  },
  type: {
    type: String,
    validator: (value) => ['employee', 'public'].includes(value),
    default: 'employee',
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
});
const emit = defineEmits(['update:modelValue']);
const { model, normalizedModelValue } = useSelectModel(props, emit);

const userOptions = ref([]);
const searchingUsers = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  userOptions.value = [];

  toSelectValues(selectedValue, props.multiple).forEach((userId) => {
    accountApi.fetchProfile(userId).then(({ result }) => {
      userOptions.value.push(result);
    });
  });
}

function searchUsers(queryString) {
  if (queryString) {
    searchingUsers.value = true;

    accountApi.fetch({
      usernameOrRealNameOrNamePinyinLike: queryString,
      isPublicAccount: props.type === 'public',
    }).then(({ result }) => {
      userOptions.value = result.content;
    }).finally(() => (searchingUsers.value = false));
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingUsers"
    :remote-method="searchUsers"
    placeholder="根据用户名、姓名或拼音搜索"
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
      v-for="userOption of userOptions"
      :key="userOption.id"
      :label="userOption.commonName"
      :value="userOption.id"
    >
      <div class="flex justify-between items-center">
        <ElSpace>
          <UserAvatar
            :src="userOption.avatarUrl"
            size="small" />
          {{ userOption.commonName }}
        </ElSpace>
        <span>{{ userOption.department?.name }}</span>
      </div>
    </ElOption>
  </ElSelect>
</template>
