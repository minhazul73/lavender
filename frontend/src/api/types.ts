export interface UserProfile {
  username: string;
  uid: number;
  gid: number;
  home: string;
  shell: string;
  groups: string[];
  is_admin: boolean;
  can_elevate: boolean;
  admin_remaining_seconds: number;
  connected?: boolean;
}

export interface LoginResponse {
  success: boolean;
  username: string;
  redirect: string;
  is_admin: boolean;
  can_elevate: boolean;
}

export interface ElevationResponse {
  success: boolean;
  is_admin: boolean;
  expires_in: number;
}

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
  temp: number;
  type?: string;
  crit?: number;
}

export interface NetworkTelemetry {
  interface: string;
  rx_bytes_sec?: number;
  tx_bytes_sec?: number;
  rx_rate?: number;
  tx_rate?: number;
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

export interface StorageDiskItem {
  filesystem: string;
  size: string;
  used: string;
  available: string;
  use_percent: string;
  mount_point: string;
}

export interface StorageOverviewResponse {
  disks: StorageDiskItem[];
}

export interface ServiceItem {
  unit: string;
  load?: string;
  active?: string;
  sub?: string;
  description?: string;
  scope?: string;
}

export interface ServicesListResponse {
  services: ServiceItem[];
  count: number;
}

export interface ProcessItem {
  pid: number;
  user: string;
  cpu: number;
  mem: number;
  command: string;
  name: string;
}

export interface ProcessesOverviewResponse {
  processes: ProcessItem[];
  load: Record<string, unknown>;
  memory: Record<string, unknown>;
}

export interface WifiNetworkItem {
  ssid: string;
  bssid?: string;
  signal?: number;
  frequency?: string;
  security?: string;
}

export interface NetworkInterfaceItem {
  name: string;
  ip?: string;
  mac?: string;
  state?: string;
  rx_bytes?: number;
  tx_bytes?: number;
  speed?: string;
}

export interface NetworkSummaryResponse {
  summary: Record<string, unknown>;
  interfaces: NetworkInterfaceItem[];
  wifi: {
    connected?: boolean;
    ssid?: string;
    signal?: number;
    networks?: WifiNetworkItem[];
  };
  dns: string[];
  dns_details: Record<string, unknown>;
  gateways: Array<Record<string, unknown>>;
}

export interface PingResponse {
  target: string;
  transmitted: number;
  received: number;
  packet_loss: number;
  avg_latency_ms?: number;
  output?: string;
  success: boolean;
}

export interface DnsQueryResponse {
  domain: string;
  resolved_ip?: string;
  latency_ms?: number;
  success: boolean;
  error?: string;
}

export interface PackageItem {
  name: string;
  version?: string;
  description?: string;
  installed?: boolean;
  upgradable?: boolean;
  new_version?: string;
}

export interface PackagesOverviewResponse {
  backend: string;
  backend_name: string;
  backend_short: string;
  installed_count: number;
  upgradable_count: number;
  upgradable: PackageItem[];
  installed: PackageItem[];
}

export interface UserSessionItem {
  user: string;
  tty: string;
  from?: string;
  login_time?: string;
  idle?: string;
}

export interface UserItem {
  username: string;
  uid: number;
  gid: number;
  home: string;
  shell: string;
  groups: string[];
  is_human: boolean;
  has_ssh_keys?: boolean;
}

export interface UsersOverviewResponse {
  human_users: UserItem[];
  system_users: UserItem[];
  groups_categorized: Record<string, string[]>;
  active_sessions: UserSessionItem[];
  login_history: Array<Record<string, unknown>>;
  security: Record<string, unknown>;
  metrics: {
    active_sessions_count: number;
    human_users_count: number;
    total_ssh_keys: number;
    is_elevated: boolean;
  };
  current_user: UserProfile;
}

export interface PowerStateResponse {
  active_governor: string;
  available_governors: string[];
  scheduled?: {
    action: string;
    time: string;
    remaining_minutes: number;
  } | null;
}
