import { describe, expect, it } from 'vitest';
import { buildBreadcrumbItems } from '@/utils/breadcrumbs';

describe('buildBreadcrumbItems', () => {
  it('uses the declared detail hierarchy instead of skipping the list page', () => {
    expect(buildBreadcrumbItems([
      { meta: { title: '系统管理' } },
      { meta: { title: '存储集群详情', breadcrumb: ['系统管理', '存储集群', '存储集群详情'] } },
    ])).toEqual([
      { label: '系统管理', title: '系统管理' },
      { label: '存储集群', title: '存储集群' },
      { label: '存储集群详情', title: '存储集群详情' },
    ]);
  });

  it('keeps ordinary matched-route breadcrumbs and omits untitled records', () => {
    expect(buildBreadcrumbItems([
      { meta: {} },
      { meta: { title: '项目组' } },
      { meta: { title: '项目组详情' } },
    ])).toEqual([
      { label: '项目组', title: '项目组' },
      { label: '项目组详情', title: '项目组详情' },
    ]);
  });

  it('replaces the current detail label with the loaded object name and keeps it as tooltip text', () => {
    expect(buildBreadcrumbItems([
      { meta: { title: '系统管理' } },
      { meta: { title: '存储集群详情', breadcrumb: ['系统管理', '存储集群', '存储集群详情'] } },
    ], '北京 NetApp')).toEqual([
      { label: '系统管理', title: '系统管理' },
      { label: '存储集群', title: '存储集群' },
      { label: '北京 NetApp详情', title: '北京 NetApp详情' },
    ]);
  });

  it('retains the static detail label when the resource request has no name', () => {
    expect(buildBreadcrumbItems([
      { meta: { title: '项目组详情', breadcrumb: ['项目组', '项目组详情'] } },
    ])).toEqual([
      { label: '项目组', title: '项目组' },
      { label: '项目组详情', title: '项目组详情' },
    ]);
  });

  it('uses a loaded project resource hierarchy when a child detail provides it', () => {
    expect(buildBreadcrumbItems([
      { meta: { title: '用户目录详情', breadcrumb: ['用户目录', '用户目录详情'] } },
    ], 'alice', ['项目', '存储平台', 'alice用户详情'])).toEqual([
      { label: '项目', title: '项目' },
      { label: '存储平台', title: '存储平台' },
      { label: 'alice用户详情', title: 'alice用户详情' },
    ]);
  });
});
