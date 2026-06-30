<script setup>
import { ElOption, ElSelect, ElSpace } from 'element-plus';
import { ref } from 'vue';
import accountApi from '@/api/account-api';
import domainGroupApi from '@/api/domain-group-api';
import { useSelectModel } from '@/composables/select-model';

const props = defineProps({
  modelValue: {
    type: [String, Number, Array],
    default: null,
  },
  multiple: {
    type: Boolean,
    default: false,
  },
  multipleLimit: {
    type: Number,
    default: 0,
  },
});
const emit = defineEmits(['update:modelValue']);
const { model } = useSelectModel(props, emit);

const userAndGroupOptions = ref([]);
const searchingUsers = ref(false);

function searchUsers(queryString) {
  let userOptions = [];
  let groupOptions = [];
  if (queryString) {
    searchingUsers.value = true;
    const userPromise = accountApi.fetch({
      usernameOrRealNameOrNamePinyinLike: queryString,
    }).then(({ result }) => {
      const useContents = result.content;
      userOptions = useContents.map((user) => ({ name: user.commonName, emailAddress: user.emailAddress, id: user.id }));
      return userOptions;
    });

    const groupPromise = domainGroupApi.fetch({
      nameLike: queryString,
      isEmailEnabled: true,
    }).then(({ result }) => {
      const groupContents = result.content;
      groupOptions = groupContents.map((group) => ({ name: group.name, emailAddress: group.emailAddress, id: group.id }));
      return groupOptions;
    });

    Promise.all([userPromise, groupPromise]).then(([userOptions, groupOptions]) => {
      userAndGroupOptions.value = [...userOptions, ...groupOptions];
      searchingUsers.value = false;
    });
  }
}
</script>

<template>
  <ElSelect
    v-model="model"
    class="w-full"
    :loading="searchingUsers"
    :remote-method="searchUsers"
    placeholder="根据用户名(拼音）、群组名搜索"
    :multiple="multiple"
    :multiple-limit="multipleLimit"
    :reserve-keyword="false"
    clearable
    default-first-option
    filterable
    remote
    remote-show-suffix
  >
    <ElOption
      v-for="userAndGroupOption of userAndGroupOptions"
      :key="userAndGroupOption.id"
      :value="userAndGroupOption.emailAddress"
    >
      <div class="flex justify-between items-center">
        <ElSpace>
          {{ userAndGroupOption.name }}({{ userAndGroupOption.emailAddress }})
        </ElSpace>
      </div>
    </ElOption>
  </ElSelect>
</template>
