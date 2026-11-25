import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useReconnect } from './useReconnect';

describe('useReconnect', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('schedules reconnection with exponential backoff up to maxDelay', () => {
    const onReconnect = vi.fn();
    const { result } = renderHook(() =>
      useReconnect({
        initialDelay: 100,
        maxDelay: 300,
        backoffFactor: 2,
        onReconnect,
      })
    );

    expect(result.current.getDelay()).toBe(100);

    // First schedule
    act(() => {
      result.current.schedule();
    });
    expect(onReconnect).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(onReconnect).toHaveBeenCalledTimes(1);
    expect(result.current.getDelay()).toBe(200);

    // Second schedule (delay is now 200)
    act(() => {
      result.current.schedule();
    });
    act(() => {
      vi.advanceTimersByTime(199);
    });
    expect(onReconnect).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onReconnect).toHaveBeenCalledTimes(2);
    // 200 * 2 = 400 capped at maxDelay 300
    expect(result.current.getDelay()).toBe(300);
  });

  it('cancels pending reconnect timer', () => {
    const onReconnect = vi.fn();
    const { result } = renderHook(() =>
      useReconnect({
        initialDelay: 100,
        onReconnect,
      })
    );

    act(() => {
      result.current.schedule();
    });
    act(() => {
      result.current.cancel();
      vi.advanceTimersByTime(200);
    });

    expect(onReconnect).not.toHaveBeenCalled();
  });

  it('resets backoff delay to initialDelay and cancels timer', () => {
    const onReconnect = vi.fn();
    const { result } = renderHook(() =>
      useReconnect({
        initialDelay: 100,
        onReconnect,
      })
    );

    act(() => {
      result.current.schedule();
      vi.advanceTimersByTime(100);
    });
    expect(result.current.getDelay()).toBe(200);

    act(() => {
      result.current.schedule();
      result.current.reset();
    });
    expect(result.current.getDelay()).toBe(100);

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onReconnect).toHaveBeenCalledTimes(1);
  });

  it('cancels timer on unmount', () => {
    const onReconnect = vi.fn();
    const { result, unmount } = renderHook(() =>
      useReconnect({
        initialDelay: 100,
        onReconnect,
      })
    );

    act(() => {
      result.current.schedule();
    });
    unmount();

    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(onReconnect).not.toHaveBeenCalled();
  });
});
