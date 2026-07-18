import { defineComponent, h } from 'vue';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import TableActionButton from '@/components/basic/TableActionButton.vue';

const ElButton = defineComponent({
  name: 'ElButton',
  props: {
    plain: Boolean,
    size: String,
    type: String,
  },
  setup(props, { attrs, slots }) {
    return () => h('button', {
      ...attrs,
      'data-plain': String(props.plain),
      'data-size': props.size,
      'data-type': props.type,
    }, slots.default?.());
  },
});

describe('TableActionButton', () => {
  it.each([
    ['create', 'success'],
    ['detail', 'info'],
    ['edit', 'primary'],
    ['delete', 'danger'],
    ['remove', 'danger'],
    ['activate', 'success'],
    ['sync', 'success'],
    ['rollback', 'success'],
  ])('renders %s as a small plain %s action', (action, type) => {
    const wrapper = mount(TableActionButton, {
      props: { action },
      slots: { default: action },
      global: { stubs: { ElButton } },
    });

    const button = wrapper.get('button');
    expect(button.attributes('data-size')).toBe('small');
    expect(button.attributes('data-plain')).toBe('true');
    expect(button.attributes('data-type')).toBe(type);
  });

  it('forwards interaction and accessibility attributes to the native Element button', async () => {
    const wrapper = mount(TableActionButton, {
      props: { action: 'detail' },
      attrs: { 'aria-label': '查看详情' },
      global: { stubs: { ElButton } },
    });

    await wrapper.get('button').trigger('click');
    expect(wrapper.get('button').attributes('aria-label')).toBe('查看详情');
  });
});
