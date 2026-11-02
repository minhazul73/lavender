import { useState, useCallback, useRef, useEffect } from 'react';

export interface AsyncDataState<T> {
  data: T | null;
  loading: boolean;
  refreshing: boolean;
  error: Error | null;
  refresh: () => void;
}

/**
 * Generic hook for async data fetching with loading/refreshing/error states.
 * On mount, calls `fetcher()` and sets loading=true.
 * Subsequent `refresh()` calls set refreshing=true instead.
 */
export function useAsyncData<T>(
  fetcher: () => Promise<T>,
): AsyncDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const load = useCallback(
    async (isRefresh: boolean) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const result = await fetcher();
        if (mountedRef.current) setData(result);
      } catch (e) {
        if (mountedRef.current) setError(e instanceof Error ? e : new Error(String(e)));
      } finally {
        if (mountedRef.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [fetcher],
  );

  useEffect(() => {
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refresh = useCallback(() => load(true), [load]);

  return { data, loading, refreshing, error, refresh };
}

