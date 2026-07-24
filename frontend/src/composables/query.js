import { ref } from 'vue';

/**
 * @template T
 * @param {() => T} defaultProvider
 */
export function useQueryParams(defaultProvider) {
  const queryParams = ref(defaultProvider());

  function reset() {
    queryParams.value = defaultProvider();
  }

  return {
    queryParams,
    reset,
  };
}

/**
 * @template T
 * @param {() => Promise<T>} request
 * @param {T} initialValue
 */
export function useQuery(request, initialValue = []) {
  const result = ref(initialValue);
  const querying = ref(false);
  const error = ref(null);

  function query() {
    querying.value = true;
    error.value = null;

    return request()
      .then((res) => {
        result.value = res;
        return res;
      })
      .catch((err) => {
        error.value = err;
        throw err;
      })
      .finally(() => {
        querying.value = false;
      });
  }

  return {
    result,
    querying,
    error,
    query,
  };
}
