import { useRef, useCallback, useEffect, useMemo } from 'react';

export interface UseReconnectOptions {
  initialDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  onReconnect: () => void;
}

export function useReconnect(options: UseReconnectOptions) {
  const {
    initialDelay = 1000,
    maxDelay = 15000,
    backoffFactor = 2,
    onReconnect,
  } = options;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const delayRef = useRef(initialDelay);
  const onReconnectRef = useRef(onReconnect);
  const initialDelayRef = useRef(initialDelay);
  const maxDelayRef = useRef(maxDelay);
  const backoffFactorRef = useRef(backoffFactor);

  useEffect(() => {
    onReconnectRef.current = onReconnect;
    initialDelayRef.current = initialDelay;
    maxDelayRef.current = maxDelay;
    backoffFactorRef.current = backoffFactor;
  }, [onReconnect, initialDelay, maxDelay, backoffFactor]);

  const cancel = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    cancel();
    delayRef.current = initialDelayRef.current;
  }, [cancel]);

  const schedule = useCallback(() => {
    cancel();
    const delay = delayRef.current;
    timerRef.current = setTimeout(() => {
      delayRef.current = Math.min(
        delayRef.current * backoffFactorRef.current,
        maxDelayRef.current
      );
      timerRef.current = null;
      onReconnectRef.current?.();
    }, delay);
  }, [cancel]);

  useEffect(() => {
    return () => {
      cancel();
    };
  }, [cancel]);

  return useMemo(
    () => ({
      schedule,
      cancel,
      reset,
      getDelay: () => delayRef.current,
    }),
    [schedule, cancel, reset]
  );
}
