import { defineComponent, h } from 'vue';
import { mount } from '@vue/test-utils';
import TimeRangePicker from '@/components/form/TimeRangePicker.vue';

const nextRange = ['2026-07-23 08:00:00', '2026-07-24 08:00:00'];

const ElDatePicker = defineComponent({
  name: 'ElDatePicker',
  inheritAttrs: false,
  props: {
    modelValue: { type: Array, default: () => [] },
    type: String,
    rangeSeparator: String,
    format: String,
    valueFormat: String,
    startPlaceholder: String,
    endPlaceholder: String,
    shortcuts: { type: Array, default: () => [] },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    return () => h('button', {
      type: 'button',
      'data-testid': 'time-range-picker',
      'data-shortcut-labels': props.shortcuts.map((shortcut) => shortcut.text).join(','),
      onClick: () => emit('update:modelValue', nextRange),
    });
  },
});

describe('TimeRangePicker', () => {
  it('standardizes the date-time range contract and emits selected ranges', async () => {
    const wrapper = mount(TimeRangePicker, {
      props: { modelValue: ['2026-07-24 00:00:00', '2026-07-24 08:00:00'] },
      global: { stubs: { ElDatePicker } },
    });
    const picker = wrapper.findComponent({ name: 'ElDatePicker' });

    expect(picker.props()).toMatchObject({
      type: 'datetimerange',
      rangeSeparator: '至',
      format: 'YYYY-MM-DD HH:mm:ss',
      valueFormat: 'YYYY-MM-DD HH:mm:ss',
      startPlaceholder: '开始日期时间',
      endPlaceholder: '结束日期时间',
    });
    expect(picker.attributes('data-shortcut-labels')).toBe('1天内,3天内,1周内,1个月内,3个月内,6个月内,1年内');

    await picker.trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[nextRange]]);
  });
});
