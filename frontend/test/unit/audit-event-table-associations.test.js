import { defineComponent, h } from 'vue';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AuditEventTable from '@/components/audit/AuditEventTable.vue';

const row = {
  id: '7af3cbd9-2be4-41f7-8af9-9892f5071c2b',
  occurred_at: '2026-07-20T15:06:53',
  actor_user_id: 9,
  actor: { id: 9, display_name: 'collector' },
  action: 'storage.collection.run',
  resource_type: 'storage_cluster',
  resource_id: '2',
  resource: { type: 'storage_cluster', id: '2', name: '华东存储集群' },
  related_projects: [
    { id: 10, name: '芯片设计平台' },
    { id: 11, name: '仿真平台' },
  ],
  relation_path: '存储集群 → 项目组 → 项目',
  outcome: 'success',
  trace_id: 'ec6ae0f4-c3a4-4e31-8a1b-b7ab88eb5f07',
};

const DataTable = defineComponent({
  name: 'DataTable',
  props: { data: Array },
  setup(_, { slots }) {
    return () => h('section', { 'data-testid': 'data-table' }, slots.default?.());
  },
});

const TableColumn = defineComponent({
  name: 'ElTableColumn',
  props: { label: String },
  setup(props, { slots }) {
    return () => h('section', { 'data-column': props.label }, slots.default?.({ row }));
  },
});

const ResourceLink = defineComponent({
  name: 'AccessibleResourceLink',
  props: { to: Object },
  setup(props, { slots }) {
    return () => h('a', { 'data-route-name': props.to?.name }, slots.default?.());
  },
});

describe('AuditEventTable associations', () => {
  it('shows an understandable resource-to-project relationship chain with accessible links', () => {
    const wrapper = mount(AuditEventTable, {
      props: { events: [row], showProject: true },
      global: {
        stubs: {
          DataTable,
          ElTableColumn: TableColumn,
          ElTag: { template: '<span><slot /></span>' },
          AccessibleResourceLink: ResourceLink,
          TableActionButton: { template: '<button><slot /></button>' },
        },
      },
    });

    expect(wrapper.get('[data-column="主体"]').text()).toContain('collector');
    expect(wrapper.get('[data-column="资源"]').text()).toContain('华东存储集群');
    expect(wrapper.get('[data-column="关联项目"]').text()).toContain('芯片设计平台');
    expect(wrapper.get('[data-column="关联项目"]').text()).toContain('仿真平台');
    expect(wrapper.get('[data-column="关联项目"]').text()).toContain('存储集群 → 项目组 → 项目');
    expect(wrapper.find('[data-route-name="StorageClusterDetail"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-route-name="ProjectDetail"]')).toHaveLength(2);
  });
});
