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

export interface BatteryInfo {
  present: boolean;
  status?: string;
  capacity?: number;
  health?: string;
  technology?: string;
  voltage_now?: number;
  current_now?: number;
  power_now?: number;
}

export interface DeviceStats {
  battery: Record<string, unknown>;
  thermal: Array<Record<string, unknown>>;
  cpu_freq: Array<Record<string, unknown>>;
  cpu_scaling: Record<string, unknown>;
  uptime: Record<string, unknown>;
}

export interface NetworkSummary {
  summary: Record<string, unknown>;
  interfaces: Array<Record<string, unknown>>;
  wifi: Record<string, unknown>;
  dns: string[];
  dns_details: Record<string, unknown>;
  gateways: Array<Record<string, unknown>>;
}

export interface PackagesOverview {
  backend: string;
  backend_name: string;
  backend_short: string;
  installed_count: number;
  upgradable_count: number;
  upgradable: Array<Record<string, unknown>>;
  installed: Array<Record<string, unknown>>;
}

export interface PowerState {
  active_governor: string;
  available_governors: string[];
  scheduled?: Record<string, unknown> | null;
}

export interface UsersOverview {
  human_users: Array<Record<string, unknown>>;
  system_users: Array<Record<string, unknown>>;
  groups_categorized: Record<string, unknown>;
  active_sessions: Array<Record<string, unknown>>;
  login_history: Array<Record<string, unknown>>;
  security: Record<string, unknown>;
  metrics: {
    active_sessions_count: number;
    human_users_count: number;
    total_ssh_keys: number;
    is_elevated: boolean;
  };
}

export interface ServiceItem {
  unit: string;
  load?: string;
  active?: string;
  sub?: string;
  description?: string;
  scope?: string;
}

export interface ProcessItem {
  pid: number;
  user: string;
  cpu: number;
  mem: number;
  command: string;
  name: string;
}

export interface DiskItem {
  filesystem: string;
  size: string;
  used: string;
  available: string;
  use_percent: string;
  mount_point: string;
}
