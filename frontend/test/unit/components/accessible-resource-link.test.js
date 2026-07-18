import { defineComponent, h } from 'vue';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { mount } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';

const router = vi.hoisted(() => ({
  push: vi.fn(),
  resolve: vi.fn(),
}));

vi.mock('vue-router', () => ({ useRouter: () => router }));

import AccessibleResourceLink from '@/components/basic/AccessibleResourceLink.vue';

const ElLink = defineComponent({
  name: 'ElLink',
  props: { type: String, underline: Boolean },
  setup(props, { attrs, slots }) {
    return () => h('a', { ...attrs, 'data-type': props.type, 'data-underline': String(props.underline) }, slots.default?.());
  },
});

function mountLink(to) {
  return mount(AccessibleResourceLink, {
    props: { to },
    slots: { default: '存储集群 A' },
    global: { stubs: { ElLink } },
  });
}

describe('AccessibleResourceLink', () => {
  it('owns the lightweight resource-link appearance instead of inheriting Element Plus primary styles', () => {
    const source = readFileSync(resolve(process.cwd(), 'src/components/basic/AccessibleResourceLink.vue'), 'utf8');

    expect(source).toContain('class="accessible-resource-link__link"');
    expect(source).toContain('font-weight: 400;');
    expect(source).toContain('color: #5b84ad;');
    expect(source).toContain('color: #4d759d;');
    expect(source).not.toContain('type="primary"');
  });

  it('renders a lightweight internal link only when the resolved route is accessible', async () => {
    router.resolve.mockReturnValue({ meta: { isAccessible: () => 200 } });
    const wrapper = mountLink({ name: 'StorageClusterDetail', params: { id: 8 } });

    const link = wrapper.get('a');
    expect(link.attributes('class')).toContain('accessible-resource-link__link');
    expect(link.attributes('data-type')).toBeUndefined();
    expect(link.attributes('data-underline')).toBe('false');
    await link.trigger('click');
    expect(router.push).toHaveBeenCalledWith({ name: 'StorageClusterDetail', params: { id: 8 } });
  });

  it.each([
    [{ name: 'StorageClusterDetail', params: { id: 8 } }, 403],
    [null, 200],
    [{ name: 'StorageClusterDetail', params: { id: null } }, 200],
  ])('keeps the label as text when the route cannot be linked', (to, status) => {
    router.resolve.mockReturnValue({ meta: { isAccessible: () => status } });
    const wrapper = mountLink(to);

    expect(wrapper.find('a').exists()).toBe(false);
    expect(wrapper.text()).toBe('存储集群 A');
  });
});
