import { computed } from 'vue';

export function normalizeSelectValue(value) {
  return value === '' ? null : value;
}

export function toSelectValues(value, multiple = false) {
  const normalizedValue = normalizeSelectValue(value);

  if (normalizedValue == null) {
    return [];
  }

  return multiple ? normalizedValue : [normalizedValue];
}

export function useSelectModel(props, emit, {
  transformOutput = (value) => value,
} = {}) {
  const normalizedModelValue = computed(() => normalizeSelectValue(props.modelValue));
  const model = computed({
    get: () => normalizedModelValue.value,
    set: (value) => emit('update:modelValue', transformOutput(normalizeSelectValue(value))),
  });

  return {
    model,
    normalizedModelValue,
  };
}
