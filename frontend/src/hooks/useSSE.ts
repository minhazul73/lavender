import { useState, useEffect, useRef, useCallback } from 'react';
import type {
  LiveTelemetryData,
  CpuInfo,
  RamInfo,
  BatteryTelemetry,
  NetworkTelemetry,
} from '../api/types/device';
import { useReconnect } from './useReconnect';

export type SSEConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export type LiveTelemetryMetric =
  | { metric: 'cpu'; data: CpuInfo }
  | { metric: 'ram'; data: RamInfo }
  | { metric: 'battery'; data: BatteryTelemetry }
  | { metric: 'thermal'; data: LiveTelemetryData['thermal'] }
  | { metric: 'network'; data: NetworkTelemetry };

export type LiveMetricCallback = <K extends LiveTelemetryMetric['metric']>(
  metric: K,
  data: Extract<LiveTelemetryMetric, { metric: K }>['data']
) => void;

interface UseSSEOptions {
  url?: string;
  enabled?: boolean;
  maxReconnectDelay?: number;
  initialReconnectDelay?: number;
  onMetric?: LiveMetricCallback;
}

export function useSSE(options: UseSSEOptions = {}) {
  const {
    url = '/api/device/live?metrics=cpu,ram,thermal,battery,network',
    enabled = true,
    initialReconnectDelay = 1000,
    maxReconnectDelay = 15000,
    onMetric,
  } = options;

  const [data, setData] = useState<LiveTelemetryData | null>(null);
  const [status, setStatus] = useState<SSEConnectionStatus>('connecting');
  const [error, setError] = useState<Error | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const onMetricRef = useRef(onMetric);
  const connectRef = useRef<() => void>(() => {});

  useEffect(() => {
    onMetricRef.current = onMetric;
  }, [onMetric]);

  const { cancel, reset, schedule } = useReconnect({
    initialDelay: initialReconnectDelay,
    maxDelay: maxReconnectDelay,
    onReconnect: () => connectRef.current(),
  });

  const closeStream = useCallback(() => {
    cancel();
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, [cancel]);

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
        reset();
      };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (parsed && typeof parsed === 'object') {
            if (parsed.metric && parsed.data !== undefined) {
              setData((prev) => ({
                ...prev,
                [parsed.metric]: parsed.data,
              }));
              if (
                parsed.metric === 'cpu' ||
                parsed.metric === 'ram' ||
                parsed.metric === 'battery' ||
                parsed.metric === 'thermal' ||
                parsed.metric === 'network'
              ) {
                onMetricRef.current?.(parsed.metric, parsed.data);
              }
            } else {
              setData((prev) => ({
                ...prev,
                ...parsed,
              }));
              Object.entries(parsed).forEach(([k, v]) => {
                if (
                  k === 'cpu' ||
                  k === 'ram' ||
                  k === 'battery' ||
                  k === 'thermal' ||
                  k === 'network'
                ) {
                  onMetricRef.current?.(k, v as any);
                }
              });
            }
          }
        } catch (err) {
          console.warn('Failed to parse SSE JSON payload:', err);
        }
      };

      es.onerror = () => {
        setStatus('disconnected');
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        schedule();
      };
    } catch (err) {
      setStatus('disconnected');
      setError(err instanceof Error ? err : new Error('Failed to initialize SSE'));
    }
  }, [url, enabled, closeStream, reset, schedule]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  // Tab visibility: pause stream in background to save device power & CPU
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        closeStream();
        setStatus('disconnected');
      } else if (enabled) {
        reset();
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [enabled, connect, closeStream, reset]);

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
