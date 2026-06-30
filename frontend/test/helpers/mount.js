import { defineComponent, h } from 'vue';

function createStub(name, tag = 'div') {
  return defineComponent({
    name,
    inheritAttrs: false,
    setup(_, { attrs, slots }) {
      return () => h(tag, attrs, slots.default ? slots.default() : []);
    },
  });
}

export const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: {
    to: {
      type: [String, Object],
      default: '',
    },
    custom: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, { slots }) {
    return () => {
      if (props.custom && slots.default) {
        return slots.default({
          href: typeof props.to === 'string' ? props.to : '/',
          navigate: () => undefined,
        });
      }

      return h('a', { href: typeof props.to === 'string' ? props.to : '/' }, slots.default ? slots.default() : []);
    };
  },
});

export const commonStubs = {
  ElLink: createStub('ElLink', 'a'),
  ElAvatar: createStub('ElAvatar'),
  ElButton: createStub('ElButton', 'button'),
  ElCard: createStub('ElCard'),
  ElConfigProvider: createStub('ElConfigProvider'),
  ElForm: createStub('ElForm', 'form'),
  ElPagination: createStub('ElPagination'),
  ElTable: createStub('ElTable'),
  ElDatePicker: createStub('ElDatePicker'),
  ElDescriptions: createStub('ElDescriptions'),
  ElDescriptionsItem: createStub('ElDescriptionsItem'),
  ElFormItem: createStub('ElFormItem'),
  ElOption: createStub('ElOption', 'option'),
  ElSelect: createStub('ElSelect', 'select'),
  RouterLink: RouterLinkStub,
  RouterView: createStub('RouterView'),
  GridContainer: createStub('GridContainer'),
  Result: createStub('Result'),
  RealTimePage: createStub('RealTimePage'),
  FilterForm: createStub('FilterForm'),
  LoadingCharts: createStub('LoadingCharts'),
  AnimatedTextChart: createStub('AnimatedTextChart'),
  DiskUsage: createStub('DiskUsage'),
  LineCharts: createStub('LineCharts'),
  MultipleLineCharts: createStub('MultipleLineCharts'),
  ICarbonUserFilled: createStub('ICarbonUserFilled'),
};
