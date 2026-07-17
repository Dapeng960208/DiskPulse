import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { mount } from '@vue/test-utils';
import StorageTypeTag from '@/components/data/StorageTypeTag.vue';

const source = (path) => readFileSync(resolve(process.cwd(), path), 'utf8');

const pairedColumnPages = [
  'src/pages/usage/UsageListPage.vue',
  'src/pages/group/GroupListPage.vue',
  'src/pages/project/components/ProjectTable.vue',
  'src/pages/project/ProjectDetailPage.vue',
  'src/pages/admin/aggregate/AggregateListPage.vue',
  'src/pages/admin/volume/VolumeListPage.vue',
  'src/pages/admin/qtree/QtreeListPage.vue',
];

describe('storage cluster display consistency', () => {
  it('renders storage types as success tags and empty values as plain placeholders', () => {
    const tagged = mount(StorageTypeTag, { props: { value: 'netapp' } });
    expect(tagged.findComponent({ name: 'ElTag' }).props('type')).toBe('success');
    expect(tagged.text()).toBe('netapp');

    const empty = mount(StorageTypeTag, { props: { value: null } });
    expect(empty.findComponent({ name: 'ElTag' }).exists()).toBe(false);
    expect(empty.text()).toBe('-');
  });

  it.each(pairedColumnPages)('%s separates cluster names from storage type tags', (path) => {
    const page = source(path);
    expect(page).toContain('label="存储集群"');
    expect(page).toContain('label="存储类型"');
    expect(page).toContain('<StorageTypeTag');
  });

  it('adds the shared storage type column to the storage cluster list', () => {
    const page = source('src/pages/admin/storage-cluster/StorageClusterListPage.vue');
    expect(page).toContain('label="集群名称"');
    expect(page).toContain('label="存储类型"');
    expect(page).toContain('<StorageTypeTag');
  });

  it('keeps project cluster names and types sourced from the same ordered summaries', () => {
    const page = source('src/pages/project/components/ProjectTable.vue');
    expect(page).toContain('row.storage_clusters');
    expect(page).not.toContain('label="集群类型"');
  });
});
