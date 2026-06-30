import { ref } from 'vue';

export function useDialog() {
  const dialogRef = ref();
  const visible = ref(false);

  function open() {
    visible.value = true;
  }

  function close() {
    visible.value = false;
  }

  return {
    dialogRef,
    visible,
    open,
    close,
  };
};
