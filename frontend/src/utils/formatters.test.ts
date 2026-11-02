import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  formatBytes,
  formatRate,
  formatMemKb,
  formatBatteryTime,
  formatLogTime,
} from './formatters';

describe('formatters utility', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  describe('formatBytes', () => {
    it('handles 0 and falsy values', () => {
      expect(formatBytes(0)).toBe('0 B');
    });

    it('formats KB, MB, GB properly', () => {
      expect(formatBytes(1024)).toBe('1 KB');
      expect(formatBytes(1024 * 1024 * 5)).toBe('5 MB');
      expect(formatBytes(1024 * 1024 * 1024 * 2.5)).toBe('2.5 GB');
    });
  });

  describe('formatRate', () => {
    it('formats bps to B/s, KB/s, MB/s', () => {
      expect(formatRate(500)).toBe('500 B/s');
      expect(formatRate(2048)).toBe('2.0 KB/s');
      expect(formatRate(5 * 1024 * 1024)).toBe('5.0 MB/s');
    });
  });

  describe('formatMemKb', () => {
    it('formats memory kB to MB and GB', () => {
      expect(formatMemKb(512)).toBe('512 kB');
      expect(formatMemKb(2048)).toBe('2.0 MB');
      expect(formatMemKb(4 * 1024 * 1024)).toBe('4.0 GB');
    });
  });

  describe('formatBatteryTime', () => {
    it('formats minutes into h/m representation', () => {
      expect(formatBatteryTime(45)).toBe('45 min');
      expect(formatBatteryTime(90)).toBe('1h 30m');
      expect(formatBatteryTime(120)).toBe('2 hrs');
      expect(formatBatteryTime(null)).toBe('—');
    });
  });

  describe('formatLogTime', () => {
    it('returns default placeholder for empty/null/undefined input', () => {
      expect(formatLogTime(null)).toEqual({ time: '•', full: '' });
      expect(formatLogTime(undefined)).toEqual({ time: '•', full: '' });
      expect(formatLogTime('')).toEqual({ time: '•', full: '' });
    });

    it('preserves pre-formatted time strings', () => {
      expect(formatLogTime('23:59:01')).toEqual({ time: '23:59:01', full: '23:59:01' });
      expect(formatLogTime('11:59 PM')).toEqual({ time: '11:59 PM', full: '11:59 PM' });
    });

    it('formats ISO-8601 timestamps into client local readable time', () => {
      // Mock system time to 2026-10-16 22:00:00 local time
      vi.useFakeTimers();
      const mockNow = new Date('2026-10-16T16:00:00Z');
      vi.setSystemTime(mockNow);

      const logIso = '2026-10-16T15:30:45Z';
      const result = formatLogTime(logIso);

      const expectedDate = new Date(logIso);
      const expectedTime = expectedDate.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      expect(result.time).toBe(expectedTime);
      expect(result.full).toContain(String(expectedDate.getFullYear()));
    });

    it('formats journalctl raw microsecond timestamps into local time', () => {
      vi.useFakeTimers();
      const mockNow = new Date('2026-10-16T16:00:00Z');
      vi.setSystemTime(mockNow);

      // 1792166401622398 microseconds = 1792166401622 ms
      const rawUs = '1792166401622398';
      const result = formatLogTime(rawUs);

      const expectedDate = new Date(1792166401622);
      const expectedTime = expectedDate.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      expect(result.time).toBe(expectedTime);
    });

    it('formats timestamps from a previous day with short date prefix', () => {
      vi.useFakeTimers();
      const mockNow = new Date('2026-10-16T16:00:00Z');
      vi.setSystemTime(mockNow);

      // A log from yesterday: 2026-10-15
      const yesterdayIso = '2026-10-15T12:00:00Z';
      const result = formatLogTime(yesterdayIso);

      const expectedDate = new Date(yesterdayIso);
      const expectedDatePart = expectedDate.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      });
      const expectedTimePart = expectedDate.toLocaleTimeString(undefined, {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });

      expect(result.time).toBe(`${expectedDatePart} ${expectedTimePart}`);
    });
  });
});
