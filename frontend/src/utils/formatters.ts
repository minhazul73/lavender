export function formatBytes(bytes: number, decimals = 1): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
}

export function formatRate(bps: number): string {
  if (bps === undefined || bps === null || isNaN(bps)) return '0 B/s';
  if (bps < 1024) return `${bps.toFixed(0)} B/s`;
  if (bps < 1024 * 1024) return `${(bps / 1024).toFixed(1)} KB/s`;
  return `${(bps / (1024 * 1024)).toFixed(1)} MB/s`;
}

export function formatMemKb(kb: number): string {
  if (kb === undefined || kb === null || isNaN(kb)) return '—';
  if (kb < 1024) return `${kb} kB`;
  if (kb < 1024 * 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${(kb / (1024 * 1024)).toFixed(1)} GB`;
}

export function formatBatteryTime(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '—';
  if (typeof val === 'number') {
    if (val >= 60) {
      const h = Math.floor(val / 60);
      const m = val % 60;
      return m > 0 ? `${h}h ${m}m` : `${h} hrs`;
    }
    return `${val} min`;
  }
  return String(val)
    .trim()
    .replace(/hours?/i, 'hrs')
    .replace(/minutes?/i, 'min');
}

export interface FormattedLogTime {
  time: string;
  full: string;
}

/**
 * Format a log timestamp into client-side local machine time.
 * Handles ISO-8601 strings, numeric epoch timestamps (microseconds/ms/s),
 * as well as pre-formatted time strings.
 */
export function formatLogTime(rawTimestamp?: string | number | null): FormattedLogTime {
  if (rawTimestamp === undefined || rawTimestamp === null || rawTimestamp === '') {
    return { time: '•', full: '' };
  }

  const str = String(rawTimestamp).trim();
  if (!str) {
    return { time: '•', full: '' };
  }

  // Preserve pre-formatted time strings like "23:59:01" or "11:59 PM"
  if (/^\d{1,2}:\d{2}(:\d{2})?( ?[AP]M)?$/i.test(str)) {
    return { time: str, full: str };
  }

  let date: Date | null = null;

  // Numeric epoch timestamps: microseconds (journalctl __REALTIME_TIMESTAMP), milliseconds, or seconds
  if (/^\d+$/.test(str)) {
    const num = Number(str);
    if (!Number.isNaN(num) && num > 0) {
      if (num > 1e12) {
        // Microseconds since epoch
        date = new Date(Math.floor(num / 1000));
      } else if (num > 1e9) {
        // Milliseconds since epoch
        date = new Date(num);
      } else {
        // Seconds since epoch
        date = new Date(num * 1000);
      }
    }
  } else {
    // Try parsing as ISO-8601 or standard date format
    const parsed = new Date(str);
    if (!Number.isNaN(parsed.getTime())) {
      date = parsed;
    }
  }

  if (!date || Number.isNaN(date.getTime())) {
    return { time: str, full: str };
  }

  // Format time in client's local machine timezone
  const timeStr = date.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  // Detailed local date & time for hover tooltip
  const fullStr = date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const now = new Date();
  const isSameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate();

  if (isSameDay) {
    return { time: timeStr, full: fullStr };
  }

  // For logs on a previous day, include short date so users know which day it occurred
  const dateStr = date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });

  return { time: `${dateStr} ${timeStr}`, full: fullStr };
}

