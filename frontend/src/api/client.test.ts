import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api, ApiError, registerElevationHandler, unregisterElevationHandler } from './client';

describe('API Client', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
    unregisterElevationHandler();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('performs GET request with JSON parsing', async () => {
    const mockData = { version: '1.0.0', platform: 'Linux' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'Content-Type': 'application/json' }),
      text: () => Promise.resolve(JSON.stringify(mockData)),
      json: () => Promise.resolve(mockData),
    });

    const result = await api.get('/api/device/info');
    expect(result).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/device/info',
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      })
    );
  });

  it('performs POST request with body serialization', async () => {
    const payload = { service: 'sshd', action: 'restart' };
    const mockResponse = { success: true };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      text: () => Promise.resolve(JSON.stringify(mockResponse)),
      json: () => Promise.resolve(mockResponse),
    });

    const result = await api.post('/api/system/services/action', payload);
    expect(result).toEqual(mockResponse);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/system/services/action',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(payload),
        credentials: 'include',
      })
    );
  });

  it('throws ApiError with detail message on non-200 responses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid parameter: port' }),
    });

    await expect(api.get('/api/test')).rejects.toThrow('Invalid parameter: port');
    try {
      await api.get('/api/test');
    } catch (err: unknown) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(400);
      expect((err as ApiError).data).toEqual({ detail: 'Invalid parameter: port' });
    }
  });

  it('triggers elevation handler on 403 administrative error and retries', async () => {
    const mockElevationHandler = vi.fn().mockResolvedValue(true);
    registerElevationHandler(mockElevationHandler);

    let callCount = 0;
    global.fetch = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve({
          ok: false,
          status: 403,
          clone: () => ({
            json: () => Promise.resolve({ detail: 'Administrative elevation required' }),
          }),
          json: () => Promise.resolve({ detail: 'Administrative elevation required' }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        text: () => Promise.resolve(JSON.stringify({ success: true, rebooted: true })),
        json: () => Promise.resolve({ success: true, rebooted: true }),
      });
    });

    const result = await api.post<{ success: boolean; rebooted: boolean }>('/api/power/reboot');
    expect(mockElevationHandler).toHaveBeenCalledTimes(1);
    expect(result).toEqual({ success: true, rebooted: true });
    expect(callCount).toBe(2);
  });
});
