import { computed, nextTick, ref } from 'vue';

/**
 * @typedef {'create' | 'update'} Mode
 */

/**
 * @template T
 * @typedef {Object} Options
 * @property {(model: import('vue').Ref<T>) => Object.<string, Array>} rules 字段校验规则
 * @property {(mode: Mode) => Promise<void>} doSubmit 提交
 * @property {(mode: Mode) => void} onSuccess 成功回调
 * @property {(mode: Mode, error: unknown) => void} onFailure 失败回调
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
  const submitting = ref(false);
  const initialSnapshot = ref(JSON.stringify(model.value));
  const isDirty = computed(() => JSON.stringify(model.value) !== initialSnapshot.value);

  function toggleSubmitting(value = !submitting.value) {
    submitting.value = value;
  }

  function edit(existing) {
    if (existing) {
      model.value = existing;
      mode.value = 'update';
    } else {
      model.value = initialModel();
      mode.value = 'create';
    }
    initialSnapshot.value = JSON.stringify(model.value);
  }

  async function submit() {
    if (submitting.value) return false;
    submitting.value = true;

    try {
      await formRef.value.validate();
    } catch {
      await nextTick();
      const invalidField = formRef.value.$el?.querySelector(
        '.el-form-item.is-error input, .el-form-item.is-error textarea, .el-form-item.is-error [tabindex]',
      );
      invalidField?.scrollIntoView?.({ block: 'center' });
      invalidField?.focus?.();
      submitting.value = false;
      return false;
    }

    try {
      await doSubmit(mode.value);
      initialSnapshot.value = JSON.stringify(model.value);
      await onSuccess?.(mode.value);
      return true;
    } catch (error) {
      await onFailure?.(mode.value, error);
      return false;
    } finally {
      submitting.value = false;
    }
  }

  return {
    formRef,
    mode,
    model,
    modelRules,
    submitting,
    isDirty,
    edit,
    submit,
    toggleSubmitting,
  };
};
