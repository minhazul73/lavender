export interface SystemInfo {
  model?: string;
  os_name?: string;
  os_pretty?: string;
  os_version?: string;
  os_id?: string;
  kernel?: string;
  arch?: string;
  hostname?: string;
  uptime?: string;
  cpu_model?: string;
  cpu_cores?: number;
  total_memory?: string;
}

export interface CpuCoreUsage {
  core: number;
  usage: number | null;
}

export interface CpuInfo {
  count: number;
  load1?: number;
  load5?: number;
  load15?: number;
  per_core_usage?: CpuCoreUsage[];
  cpus?: Array<{
    core: number;
    frequency_mhz: number | null;
  }>;
}

export interface RamInfo {
  total?: number;
  used?: number;
  available?: number;
  free?: number;
  used_pct?: number;
  cached?: number;
  buffers?: number;
  swap_total?: number;
  swap_used?: number;
  swap_pct?: number;
}

export interface BatteryTelemetry {
  present?: boolean;
  percentage?: number;
  state?: string;
  battery_state?: string;
  charging?: boolean;
  discharging?: boolean;
  voltage?: number;
  energy_rate?: number;
  energy?: number;
  energy_full?: number;
  temperature?: number;
  capacity?: number;
  health?: string;
  time_to_empty?: number | string;
  time_to_full?: number | string;
}

export interface ThermalZone {
  name: string;
  display_name?: string;
  temp?: number;
  temp_celsius?: number;
  temp_millicelsius?: number;
  type?: string;
  warning?: boolean;
  crit?: number | boolean;
}

export interface NetworkTelemetry {
  iface?: string;
  interface?: string;
  rx_bytes?: number;
  tx_bytes?: number;
  rx_rate_bps?: number;
  tx_rate_bps?: number;
  rx_rate?: number;
  tx_rate?: number;
  rx_bytes_sec?: number;
  tx_bytes_sec?: number;
}

export interface LiveTelemetryData {
  cpu?: CpuInfo;
  ram?: RamInfo;
  battery?: BatteryTelemetry;
  thermal?: {
    zones?: ThermalZone[];
  } | ThermalZone[];
  network?: NetworkTelemetry;
}

