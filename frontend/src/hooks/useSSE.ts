import { useState, useEffect, useRef, useCallback } from 'react';
import { LiveTelemetryData } from '../api/types';

export type SSEConnectionStatus = 'connected' | 'connecting' | 'disconnected';

interface UseSSEOptions {
  url?: string;
  enabled?: boolean;
  maxReconnectDelay?: number;
  initialReconnectDelay?: number;
}

export function useSSE(options: UseSSEOptions = {}) {
  const {
    url = '/api/device/live?metrics=cpu,ram,thermal,battery,network',
    enabled = true,
    initialReconnectDelay = 1000,
    maxReconnectDelay = 15000,
  } = options;

  const [data, setData] = useState<LiveTelemetryData | null>(null);
  const [status, setStatus] = useState<SSEConnectionStatus>('connecting');
  const [error, setError] = useState<Error | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef(initialReconnectDelay);

  const closeStream = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled || typeof EventSource === 'undefined') return;

    closeStream();
    setStatus('connecting');
    setError(null);

    try {
      const es = new EventSource(url, { withCredentials: true });
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus('connected');
        reconnectDelayRef.current = initialReconnectDelay;
      };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          setData((prev) => ({
            ...prev,
            ...parsed,
          }));
        } catch (err) {
          console.warn('Failed to parse SSE JSON payload:', err);
        }
      };

      es.onerror = () => {
        setStatus('disconnected');
        closeStream();

        // Queue reconnect
        reconnectTimerRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(
            reconnectDelayRef.current * 2,
            maxReconnectDelay
          );
          connect();
        }, reconnectDelayRef.current);
      };
    } catch (err) {
      setStatus('disconnected');
      setError(err instanceof Error ? err : new Error('Failed to initialize SSE'));
    }
  }, [url, enabled, initialReconnectDelay, maxReconnectDelay, closeStream]);

  // Tab visibility: pause stream in background to save device power & CPU
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        closeStream();
        setStatus('disconnected');
      } else if (enabled) {
        reconnectDelayRef.current = initialReconnectDelay;
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, initialReconnectDelay, connect, closeStream]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      closeStream();
      setStatus('disconnected');
    }

    return () => {
      closeStream();
    };
  }, [enabled, connect, closeStream]);

  return {
    data,
    status,
    error,
    reconnect: connect,
  };
}
