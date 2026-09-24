import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useSSE } from './useSSE';

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  withCredentials?: boolean;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;
  closed = false;

  constructor(url: string, eventSourceInitDict?: EventSourceInit) {
    this.url = url;
    this.withCredentials = eventSourceInitDict?.withCredentials;
    MockEventSource.instances.push(this);
    // Simulate auto-open
    setTimeout(() => {
      if (!this.closed && this.onopen) {
        this.onopen();
      }
    }, 0);
  }

  close() {
    this.closed = true;
  }

  // Helper for test to dispatch incoming message
  emitMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper for test to dispatch error
  emitError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

describe('useSSE Hook', () => {
  const originalEventSource = global.EventSource;

  beforeEach(() => {
    MockEventSource.instances = [];
    // @ts-expect-error Mocking global EventSource
    global.EventSource = MockEventSource;
    vi.useFakeTimers();
  });

  afterEach(() => {
    global.EventSource = originalEventSource;
    vi.useRealTimers();
  });

  it('initializes EventSource with credentials and connects', async () => {
    const { result } = renderHook(() => useSSE({ url: '/api/test/stream' }));

    expect(result.current.status).toBe('connecting');
    expect(MockEventSource.instances.length).toBe(1);
    expect(MockEventSource.instances[0].withCredentials).toBe(true);

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    expect(result.current.status).toBe('connected');
  });

  it('updates telemetry data on incoming message', async () => {
    const { result } = renderHook(() => useSSE({ url: '/api/test/stream' }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const mockPayload = {
      cpu: { count: 4, load1: 0.5, load5: 0.8, load15: 0.9 },
      ram: { total: 4096, used: 2048, used_pct: 50 },
    };

    act(() => {
      MockEventSource.instances[0].emitMessage(mockPayload);
    });

    expect(result.current.data?.cpu?.count).toBe(4);
    expect(result.current.data?.ram?.used_pct).toBe(50);
  });

  it('handles disconnect and attempts reconnection', async () => {
    const { result } = renderHook(() =>
      useSSE({ url: '/api/test/stream', initialReconnectDelay: 500 })
    );

    await act(async () => {
      vi.advanceTimersByTime(10);
    });
    expect(result.current.status).toBe('connected');

    act(() => {
      MockEventSource.instances[0].emitError();
    });

    expect(result.current.status).toBe('disconnected');

    // Fast-forward through reconnect timer
    await act(async () => {
      vi.advanceTimersByTime(600);
    });

    expect(MockEventSource.instances.length).toBe(2);
  });

  it('closes EventSource when unmounted', async () => {
    const { unmount } = renderHook(() => useSSE({ url: '/api/test/stream' }));

    await act(async () => {
      vi.advanceTimersByTime(10);
    });

    const instance = MockEventSource.instances[0];
    expect(instance.closed).toBe(false);

    unmount();
    expect(instance.closed).toBe(true);
  });
});
