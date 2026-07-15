import { defineComponent, h } from 'vue';
import { mount } from '@vue/test-utils';

import QueryForm from '@/components/form/QueryForm.vue';

const ElForm = defineComponent({
  name: 'ElForm',
  setup(_, { slots }) {
    return () => h('form', slots.default?.());
  },
});

const ElButton = defineComponent({
  name: 'ElButton',
  inheritAttrs: false,
  props: {
    type: { type: String, default: undefined },
  },
  setup(props, { attrs, slots }) {
    return () => h('button', { ...attrs, 'data-type': props.type }, slots.default?.());
  },
});

function mountQueryForm() {
  return mount(QueryForm, {
    props: { advancedCount: 2 },
    slots: {
      default: '<label data-test="primary-filter">主筛选</label>',
      advanced: '<label data-test="advanced-filter">高级筛选</label>',
      'active-filters': '<span data-test="active-filter">项目组标签：核心组</span>',
      actions: '<button type="button">辅助操作</button>',
      exportExcel: '<span />',
    },
    global: {
      stubs: {
        ElForm,
        ElButton,
      },
    },
  });
}

describe('QueryForm progressive filter toolbar', () => {
  it('keeps primary fields visible and toggles advanced fields against active chips', async () => {
    const wrapper = mountQueryForm();

    expect(wrapper.find('[data-test="primary-filter"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="advanced-filter"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="active-filter"]').exists()).toBe(true);
    expect(wrapper.find('.query-form__fields').exists()).toBe(true);

    const moreButton = wrapper.findAll('button').find((button) => button.text().includes('更多筛选'));
    expect(moreButton.text()).toContain('2');
    expect(moreButton.attributes('aria-expanded')).toBe('false');

    await moreButton.trigger('click');

    expect(wrapper.find('[data-test="advanced-filter"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="active-filter"]').exists()).toBe(false);
    expect(moreButton.attributes('aria-expanded')).toBe('true');
    expect(moreButton.text()).toContain('收起筛选');
  });

  it('orders secondary actions before reset and the rightmost primary search action', async () => {
    const wrapper = mountQueryForm();
    const buttons = wrapper.findAll('button');

    expect(buttons.map((button) => button.text().trim())).toEqual([
      '辅助操作',
      '更多筛选 · 2',
      '重置',
      '导出',
      '搜索',
    ]);
    expect(buttons[3].attributes('data-type')).toBe('success');

    await buttons[3].trigger('click');
    await buttons[2].trigger('click');
    await buttons[4].trigger('click');

    expect(wrapper.emitted('export')).toHaveLength(1);
    expect(wrapper.emitted('reset')).toHaveLength(1);
    expect(wrapper.emitted('query')).toHaveLength(1);
  });
});
