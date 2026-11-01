export interface NetworkInterfaceAddress {
  address: string;
  cidr: string;
  broadcast?: string | null;
  scope?: string;
}

export interface NetworkInterfaceStats {
  rx_bytes: number;
  tx_bytes: number;
  rx_packets: number;
  tx_packets: number;
  rx_errors?: number;
  tx_errors?: number;
}

export interface NetworkInterfaceItem {
  name: string;
  ip?: string;
  mac?: string | null;
  state?: string;
  type?: string;
  category?: 'wireless' | 'ethernet' | 'loopback' | 'bridge' | 'virtual' | 'cellular' | string;
  is_up?: boolean;
  is_default?: boolean;
  mtu?: number;
  speed?: string | null;
  flags?: string[];
  addresses?: string[];
  ipv4?: NetworkInterfaceAddress[];
  ipv6?: NetworkInterfaceAddress[];
  rx_bytes?: number;
  tx_bytes?: number;
  rx_bytes_fmt?: string;
  tx_bytes_fmt?: string;
  stats?: NetworkInterfaceStats;
}

export interface WifiNetworkItem {
  ssid: string;
  bssid?: string;
  signal?: number;
  frequency?: string;
  security?: string;
  channel?: string;
  rate?: string;
  mode?: string;
  is_current?: boolean;
}

export interface WifiDetails {
  has_hardware?: boolean;
  connected?: boolean;
  interface?: string | null;
  ssid?: string | null;
  bssid?: string | null;
  signal_percent?: number | null;
  signal_dbm?: string | null;
  quality?: string | null;
  frequency?: string | null;
  channel?: string | null;
  bitrate?: string | null;
  tx_power?: string | null;
  security?: string | null;
  mode?: string | null;
  driver?: string | null;
  nearby?: WifiNetworkItem[];
  networks?: WifiNetworkItem[];
  available_interfaces?: string[];
  rfkill_blocked?: boolean;
  message?: string | null;
  source?: string | null;
}

export interface DnsServerItem {
  ip: string;
  provider: string;
  is_primary: boolean;
  is_stub?: boolean;
}

export interface DnsDetails {
  servers?: DnsServerItem[];
  upstream_ips?: string[];
  has_local_stub?: boolean;
  stub_ip?: string | null;
  search_domains?: string[];
  resolver_type?: string;
}

export interface GatewayItem {
  gateway: string;
  interface: string;
  protocol?: string;
  metric?: number;
  prefsrc?: string;
}

export interface NetworkSummaryInfo {
  is_online?: boolean;
  primary_interface?: string | null;
  primary_type?: string | null;
  primary_ip?: string | null;
  primary_mac?: string | null;
  default_gateway?: string | null;
  primary_dns?: string | null;
  primary_dns_provider?: string | null;
  total_rx_fmt?: string;
  total_tx_fmt?: string;
  wifi_connected?: boolean;
  wifi_ssid?: string | null;
  wifi_signal?: number | null;
}

export interface NetworkSummaryResponse {
  summary: NetworkSummaryInfo;
  interfaces: NetworkInterfaceItem[];
  wifi: WifiDetails;
  dns: string[];
  dns_details: DnsDetails;
  gateways: GatewayItem[];
}

export interface PingResponse {
  target: string;
  transmitted: number;
  received: number;
  packet_loss?: number;
  packet_loss_percent?: number;
  min_latency?: number | null;
  avg_latency?: number | null;
  max_latency?: number | null;
  mdev_latency?: number | null;
  avg_latency_ms?: number | null;
  output?: string;
  error?: string;
  success: boolean;
}

export interface DnsQueryResponse {
  domain: string;
  resolved_ip?: string;
  time_ms?: number;
  latency_ms?: number;
  ipv4?: string[];
  ipv6?: string[];
  count?: number;
  success: boolean;
  error?: string;
}
