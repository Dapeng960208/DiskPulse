import { ElMessageBox } from 'element-plus';
import { ref, unref } from 'vue';

export function useDialog({ isDirty, isBusy } = {}) {
  const dialogRef = ref();
  const visible = ref(false);

  function open() {
    visible.value = true;
  }

  async function requestClose(done) {
    if (unref(isBusy)) return false;

    if (unref(isDirty)) {
      try {
        await ElMessageBox.confirm(
          '当前修改尚未保存，确认放弃吗？',
          '放弃未保存的修改？',
          {
            type: 'warning',
            confirmButtonText: '放弃修改',
            cancelButtonText: '继续编辑',
          },
        );
      } catch {
        return false;
      }
    }

    done();
    return true;
  }

  function close() {
    return requestClose(() => {
      visible.value = false;
    });
  }

  function beforeClose(done) {
    return requestClose(done);
  }

  function forceClose() {
    visible.value = false;
  }

  return {
    dialogRef,
    visible,
    open,
    close,
    beforeClose,
    forceClose,
  };
};
