import { useToggle } from '@vueuse/core';
import { computed, ref } from 'vue';

/**
 * @typedef {'create' | 'update'} Mode
 */

/**
 * @template T
 * @typedef {Object} Options
 * @property {(model: import('vue').Ref<T>) => Object.<string, Array>} rules 字段校验规则
 * @property {(mode: Mode) => Promise<void>} doSubmit 提交
 * @property {(mode: Mode) => void} onSuccess 成功回调
 * @property {(mode: Mode) => void} onFailure 失败回调
 */

/**
 * @template T
 * @param {() => T} initialModel
 * @param {Options<T>} param1
 * @returns
 */
export function useForm(initialModel, {
  rules,
  doSubmit,
  onSuccess,
  onFailure,
}) {
  const formRef = ref();
  const mode = ref('create');
  const model = ref(initialModel());
  const modelRules = computed(() => rules(model));
  const [submitting, toggleSubmitting] = useToggle();

  function edit(existing) {
    if (existing) {
      model.value = existing;
      mode.value = 'update';
    } else {
      model.value = initialModel();
      mode.value = 'create';
    }
  }

  function submit() {
    formRef.value.validate().then(() => {
      toggleSubmitting();
      return doSubmit(mode.value)
        .then(() => onSuccess(mode.value))
        .catch(() => onFailure(mode.value))
        .finally(toggleSubmitting);
    }).catch(() => {});
  }

  return {
    formRef,
    mode,
    model,
    modelRules,
    submitting,
    edit,
    submit,
    toggleSubmitting,
  };
};
