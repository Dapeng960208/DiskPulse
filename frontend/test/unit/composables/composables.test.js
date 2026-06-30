import { flushPromises } from '@vue/test-utils';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import { useQuery, useQueryParams } from '@/composables/query';

describe('composables', () => {
  it('tracks dialog visibility', () => {
    const dialog = useDialog();

    expect(dialog.visible.value).toBe(false);
    dialog.open();
    expect(dialog.visible.value).toBe(true);
    dialog.close();
    expect(dialog.visible.value).toBe(false);
  });

  it('resets query params from a provider', () => {
    const { queryParams, reset } = useQueryParams(() => ({ page: 1, size: 20 }));

    queryParams.value.page = 2;
    reset();

    expect(queryParams.value).toEqual({ page: 1, size: 20 });
  });

  it('queries async data and toggles the loading state', async () => {
    const request = vi.fn(() => Promise.resolve({ content: [1, 2] }));
    const queryState = useQuery(request, { content: [] });

    const promise = queryState.query();
    expect(queryState.querying.value).toBe(true);

    await promise;

    expect(queryState.querying.value).toBe(false);
    expect(queryState.result.value).toEqual({ content: [1, 2] });
  });

  it('submits forms and switches mode based on editing state', async () => {
    const doSubmit = vi.fn(() => Promise.resolve());
    const onSuccess = vi.fn();
    const onFailure = vi.fn();
    const form = useForm(
      () => ({ name: '' }),
      {
        rules: () => ({ name: [{ required: true }] }),
        doSubmit,
        onSuccess,
        onFailure,
      },
    );

    form.formRef.value = {
      validate: vi.fn(() => Promise.resolve()),
    };

    form.edit({ name: 'existing' });
    expect(form.mode.value).toBe('update');
    expect(form.model.value).toEqual({ name: 'existing' });

    form.submit();
    await flushPromises();

    expect(doSubmit).toHaveBeenCalledWith('update');
    expect(onSuccess).toHaveBeenCalledWith('update');
    expect(onFailure).not.toHaveBeenCalled();
  });
});
