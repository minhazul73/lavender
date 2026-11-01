export interface SystemLogEntry {
  timestamp?: string;
  message?: string;
  service?: string;
  level?: string;
}

export type SystemLogItem = string | SystemLogEntry;

export interface SystemLogsResponse {
  logs: SystemLogItem[];
  count?: number;
  service?: string;
}
