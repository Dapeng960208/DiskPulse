import { nextTick } from 'vue';
import { normalizeSelectValue, toSelectValues, useSelectModel } from '@/composables/select-model';

describe('select-model composable', () => {
  it('normalizes empty string values to null', () => {
    expect(normalizeSelectValue('')).toBeNull();
    expect(normalizeSelectValue(1)).toBe(1);
    expect(normalizeSelectValue(['a'])).toEqual(['a']);
  });

  it('expands normalized values into a selectable array', () => {
    expect(toSelectValues(null, false)).toEqual([]);
    expect(toSelectValues('', false)).toEqual([]);
    expect(toSelectValues(7, false)).toEqual([7]);
    expect(toSelectValues([1, 2], true)).toEqual([1, 2]);
  });

  it('exposes a computed model that emits normalized values', async () => {
    const props = {
      modelValue: '',
    };
    const emit = vi.fn();
    const { model, normalizedModelValue } = useSelectModel(props, emit);

    expect(normalizedModelValue.value).toBeNull();
    expect(model.value).toBeNull();

    model.value = '';
    await nextTick();

    expect(emit).toHaveBeenCalledWith('update:modelValue', null);
  });

  it('supports transforming the emitted value before update', async () => {
    const props = {
      modelValue: [1, 2],
      multiple: true,
    };
    const emit = vi.fn();
    const { model } = useSelectModel(props, emit, {
      transformOutput: (value) => value.map((item) => `host-${item}`),
    });

    model.value = [3, 4];
    await nextTick();

    expect(emit).toHaveBeenCalledWith('update:modelValue', ['host-3', 'host-4']);
  });
});
