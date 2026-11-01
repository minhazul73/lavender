export interface ProcessItem {
  pid: number;
  user: string;
  cpu: number;
  cpu_time?: number;
  time?: string;
  mem: number;
  mem_pct?: number;
  vsz?: number;
  rss?: number;
  stat?: string;
  command: string;
  name: string;
}

export interface ProcessesOverviewResponse {
  processes: ProcessItem[];
  load: {
    '1min'?: number;
    '5min'?: number;
    '15min'?: number;
    '1m'?: number;
    '5m'?: number;
    '15m'?: number;
    load1?: number;
    load5?: number;
    load15?: number;
    running?: string | number;
    total?: string | number;
    uptime_seconds?: number;
    uptime_formatted?: string;
    [key: string]: unknown;
  };
  memory: {
    raw?: string;
    error?: string;
    parsed?: {
      total?: string;
      used?: string;
      free?: string;
      shared?: string;
      percent?: number;
      swap_total?: string;
      swap_used?: string;
      swap_free?: string;
    };
    [key: string]: unknown;
  };
}
