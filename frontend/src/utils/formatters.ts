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
