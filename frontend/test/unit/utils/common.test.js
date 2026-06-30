import { flushPromises } from '@vue/test-utils';
import { vi } from 'vitest';

const ElMessage = vi.fn();
ElMessage.success = vi.fn();

const confirmMock = vi.fn();
const syncLsfConfigFile = vi.fn(() => Promise.resolve());

vi.mock('element-plus', () => ({
  ElMessage,
  ElMessageBox: {
    confirm: confirmMock,
  },
}));

vi.mock('@/api/config-api', () => ({
  default: {
    syncLsfConfigFile,
  },
}));

const { exportReport } = await import('@/utils/common');
const { confirmSync } = await import('@/composables/common');

describe('utils/common and composables/common', () => {
  beforeEach(() => {
    ElMessage.mockReset();
    ElMessage.success.mockReset();
    confirmMock.mockReset();
    syncLsfConfigFile.mockClear();
    document.body.innerHTML = '';
  });

  it('exports report blobs and shows a success message', async () => {
    const click = vi.fn();
    const appendSpy = vi.spyOn(document.body, 'appendChild');
    const removeSpy = vi.spyOn(document.body, 'removeChild');
    const originalCreateElement = document.createElement.bind(document);
    const anchor = originalCreateElement('a');
    anchor.click = click;
    const createSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName) => {
      return tagName === 'a' ? anchor : originalCreateElement(tagName);
    });

    await exportReport(Promise.resolve({
      data: new Blob(['x']),
      headers: {
        filename: encodeURIComponent('report.csv'),
      },
    }));
    await flushPromises();

    expect(click).toHaveBeenCalled();
    expect(appendSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
    expect(ElMessage).toHaveBeenCalledWith(expect.objectContaining({ type: 'success' }));

    createSpy.mockRestore();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it('shows an error message when export fails', async () => {
    await exportReport(Promise.reject(new Error('failed')));
    await flushPromises();

    expect(ElMessage).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' }));
  });

  it('confirms and runs config sync', async () => {
    confirmMock.mockImplementation((_message, _title, options) => {
      const instance = { confirmButtonLoading: false };
      return Promise.resolve(options.beforeClose('confirm', instance, vi.fn()));
    });

    confirmSync();
    await flushPromises();

    expect(confirmMock).toHaveBeenCalled();
    expect(syncLsfConfigFile).toHaveBeenCalled();
    expect(ElMessage.success).toHaveBeenCalled();
  });
});
