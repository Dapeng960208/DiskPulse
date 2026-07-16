import { flushPromises } from '@vue/test-utils';
import { ref } from 'vue';
import { useDialog } from '@/composables/dialog';
import { useForm } from '@/composables/form';
import { useQuery, useQueryParams } from '@/composables/query';

const confirmClose = vi.hoisted(() => vi.fn());

vi.mock('element-plus', () => ({
  ElMessageBox: {
    confirm: confirmClose,
  },
}));

describe('composables', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

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

  it('tracks form changes and clears dirty state after a successful submit', async () => {
    const form = useForm(
      () => ({ name: '' }),
      {
        rules: () => ({}),
        doSubmit: vi.fn(() => Promise.resolve()),
        onSuccess: vi.fn(),
        onFailure: vi.fn(),
      },
    );
    form.formRef.value = { validate: vi.fn(() => Promise.resolve()) };

    form.edit();
    expect(form.isDirty.value).toBe(false);
    form.model.value.name = 'changed';
    expect(form.isDirty.value).toBe(true);

    await form.submit();

    expect(form.isDirty.value).toBe(false);
  });

  it('prevents duplicate submissions while a request is pending', async () => {
    let finishSubmit;
    const doSubmit = vi.fn(() => new Promise((resolve) => {
      finishSubmit = resolve;
    }));
    const form = useForm(
      () => ({ name: 'demo' }),
      {
        rules: () => ({}),
        doSubmit,
        onSuccess: vi.fn(),
        onFailure: vi.fn(),
      },
    );
    form.formRef.value = { validate: vi.fn(() => Promise.resolve()) };

    const first = form.submit();
    const second = form.submit();
    await flushPromises();

    expect(form.submitting.value).toBe(true);
    expect(doSubmit).toHaveBeenCalledTimes(1);

    finishSubmit();
    await Promise.all([first, second]);
    expect(form.submitting.value).toBe(false);
  });

  it('focuses and scrolls to the first invalid field after validation fails', async () => {
    const invalidField = {
      focus: vi.fn(),
      scrollIntoView: vi.fn(),
    };
    const form = useForm(
      () => ({ name: '' }),
      {
        rules: () => ({}),
        doSubmit: vi.fn(),
        onSuccess: vi.fn(),
        onFailure: vi.fn(),
      },
    );
    form.formRef.value = {
      validate: vi.fn(() => Promise.reject(new Error('invalid'))),
      $el: {
        querySelector: vi.fn(() => invalidField),
      },
    };

    await form.submit();

    expect(invalidField.scrollIntoView).toHaveBeenCalledWith({ block: 'center' });
    expect(invalidField.focus).toHaveBeenCalled();
  });

  it('guards dirty dialog close, supports Element Plus before-close, and blocks busy close', async () => {
    const isDirty = ref(true);
    const isBusy = ref(false);
    confirmClose.mockResolvedValue();
    const dialog = useDialog({ isDirty, isBusy });

    dialog.open();
    await dialog.close();
    expect(confirmClose).toHaveBeenCalledWith(
      '当前修改尚未保存，确认放弃吗？',
      '放弃未保存的修改？',
      expect.objectContaining({ confirmButtonText: '放弃修改' }),
    );
    expect(dialog.visible.value).toBe(false);

    dialog.open();
    isDirty.value = false;
    const done = vi.fn();
    await dialog.beforeClose(done);
    expect(done).toHaveBeenCalledOnce();

    dialog.open();
    isBusy.value = true;
    await dialog.close();
    expect(dialog.visible.value).toBe(true);
  });

  it('keeps a dirty dialog open when discard confirmation is cancelled', async () => {
    confirmClose.mockRejectedValue(new Error('cancel'));
    const dialog = useDialog({ isDirty: ref(true) });

    dialog.open();
    await dialog.close();

    expect(dialog.visible.value).toBe(true);
  });
});
