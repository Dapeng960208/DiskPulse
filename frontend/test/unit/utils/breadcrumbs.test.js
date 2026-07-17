import { describe, expect, it } from 'vitest';
import { buildBreadcrumbItems } from '@/utils/breadcrumbs';

describe('buildBreadcrumbItems', () => {
  it('uses the declared detail hierarchy instead of skipping the list page', () => {
    expect(buildBreadcrumbItems([
      { meta: { title: '系统管理' } },
      { meta: { title: '存储集群详情', breadcrumb: ['系统管理', '存储集群', '存储集群详情'] } },
    ])).toEqual(['系统管理', '存储集群', '存储集群详情']);
  });

  it('keeps ordinary matched-route breadcrumbs and omits untitled records', () => {
    expect(buildBreadcrumbItems([
      { meta: {} },
      { meta: { title: '项目组' } },
      { meta: { title: '项目组详情' } },
    ])).toEqual(['项目组', '项目组详情']);
  });
});
