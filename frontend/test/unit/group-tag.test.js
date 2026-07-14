import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { vi } from 'vitest';

vi.mock('@/api/support/base-request', () => ({ default: {} }));
vi.mock('@/api/support/auth-request', () => ({ default: {} }));

describe('group tags', () => {
  it('uses a global paginated tag API', async () => {
    const { default: BaseApi } = await import('@/api/support/base-api');
    const get = vi.spyOn(BaseApi.prototype, 'get').mockResolvedValue({ content: [], total: 0 });
    const { default: groupTagApi } = await import('@/api/group-tag-api');

    await groupTagApi.fetch({ page: 1, size: 100 });

    expect(groupTagApi.urlPrefix).toBe('/group-tags');
    expect(get).toHaveBeenCalledWith('', { page: 1, size: 100 }, undefined);
  });

  it('keeps only the environment name in the tag editor', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/group-tag/components/GroupTagFormDialog.vue'),
      'utf8',
    );

    expect(source).toContain('model.name');
    expect(source).not.toMatch(/project_id|storage_cluster_id|description|is_active|StorageClusterSelect/);
  });

  it('submits project, cluster, and environment tag ids from the group form', () => {
    const source = readFileSync(
      resolve(process.cwd(), 'src/pages/group/components/GroupFormDialog.vue'),
      'utf8',
    );

    expect(source).toContain('<StorageClusterSelect');
    expect(source).toContain('<GroupTagSelect');
    expect(source).toMatch(/payload\.project_id\s*=\s*model\.value\.project_id/);
    expect(source).toMatch(/payload\.storage_cluster_id\s*=\s*model\.value\.storage_cluster_id/);
    expect(source).toMatch(/payload\.group_tag_id\s*=\s*model\.value\.group_tag_id/);
    expect(source).not.toMatch(/ProjectStorageEnvironment|project_environment/);
  });
});
