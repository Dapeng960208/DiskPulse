import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '234' } }),
}));

vi.mock('@/pages/common/RealTimePage.vue', () => ({
  default: {
    name: 'RealTimePage',
    props: ['attributeId', 'apiType', 'label'],
    template: '<div><slot name="extra-descriptions" :info="{}" /></div>',
  },
}));

vi.mock('@/api/capacity-prediction-api.js', () => ({
  default: {
    access: vi.fn(() => Promise.reject({ response: { status: 403 } })),
  },
}));

import UsageDetailPage from '@/pages/usage/UsageDetailPage.vue';

const hiddenLabels = [
  '文件数量',
  '目录权限',
  '访问时间(Access Time)',
  '修改时间(Modify Time)',
  '改变时间(Change Time)',
  '创建时间',
  '权限组',
  'Inode编号',
  '硬链接数量',
  '系统的I/O块大小',
  'IO块(IO Block)',
  '设备的标识号',
];

describe('usage detail extended field visibility', () => {
  it('does not render the temporarily hidden second through fourth rows', () => {
    const wrapper = mount(UsageDetailPage, {
      global: {
        stubs: {
          ElDescriptionsItem: {
            props: ['label'],
            template: '<div>{{ label }}</div>',
          },
        },
      },
    });

    hiddenLabels.forEach((label) => expect(wrapper.text()).not.toContain(label));
  });

  it('keeps the hidden field bindings in a temporary source comment', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/usage/UsageDetailPage.vue'),
      'utf8',
    );

    expect(source).toContain('暂时隐藏第 2–4 行扩展字段');
    hiddenLabels.forEach((label) => expect(source).toContain(`label="${label}"`));
  });
});
