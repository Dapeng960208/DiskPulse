<script setup>
import { ref, watch } from 'vue';
import { ElOption, ElSelect, ElSpace } from 'element-plus';
import rdUsersApi from '@/api/users-api.js';
import UserAvatar from '@/components/data/UserAvatar.vue';
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
const userOptions = ref([]);
const searchingUsers = ref(false);

watch(normalizedModelValue, initDefaultOptions, { immediate: true });

function initDefaultOptions(selectedValue) {
  userOptions.value = [];

  if (props.multiple) {
    if (props.initOption.length > 0) {
      userOptions.value = [...props.initOption];
    } else {
      toSelectValues(selectedValue, true).forEach((userId) => {
        rdUsersApi.fetchById(userId).then((result) => {
          userOptions.value.push(result);
        });
      });
    }
  } else if (selectedValue != null) {
    rdUsersApi.fetchById(selectedValue).then((result) => {
      userOptions.value.push(result);
    });
  }

  if (userOptions.value.length === 0) {
    rdUsersApi.fetch({ page: 1, size: 20 }).then((result) => {
      userOptions.value = result.content;
    });
  }
}

// 搜索用户
function searchUsers(queryString) {
  if (queryString) {
    searchingUsers.value = true;
    rdUsersApi.fetch({ nameLike: queryString }).then(({ content }) => {
      userOptions.value = content;
    }).finally(() => {
      searchingUsers.value = false;
    });
  }
}

// 获取选项字段
function getOptionField(value) {
  const option = userOptions.value.find((opt) => opt.id === value);
  return option ? option[props.returnField] : value;
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingUsers"
    :remote-method="searchUsers"
    placeholder="根据用户名搜索"
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
      v-for="userOption of userOptions"
      :key="userOption.id"
      :label="userOption.rd_username"
      :value="userOption.id"
    >
      <div class="flex justify-between items-center">
        <ElSpace>
          <UserAvatar
            v-if="userOption.avatar_url"
            :src="userOption.avatar_url"
            size="small" />
          {{ userOption.rd_username }} {{ userOption.username === null ? '无系统信息': userOption.username }}
        </ElSpace>
        <span>{{ userOption.department }}</span>
      </div>

    </ElOption>
  </ElSelect>
</template>
