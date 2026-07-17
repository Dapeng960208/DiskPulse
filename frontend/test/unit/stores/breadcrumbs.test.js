import { beforeEach, describe, expect, it } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useBreadcrumbs } from '@/stores/breadcrumbs';

describe('breadcrumb store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('keeps a detail title scoped to its current route and clears stale titles', () => {
    const breadcrumbs = useBreadcrumbs();

    breadcrumbs.setDetailTitle('UsagesDetail', 'alice详情');
    breadcrumbs.setDetailTitle('UsagesDetail', '');

    expect(breadcrumbs.detailTitleFor('UsagesDetail')).toBe('');
    expect(breadcrumbs.detailTitleFor('GroupDetail')).toBe('');
  });
});
