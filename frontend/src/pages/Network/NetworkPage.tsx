import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { api } from '../../api/client';
import {
  NetworkSummaryResponse,
  NetworkInterfaceItem,
  WifiNetworkItem,
  PingResponse,
  DnsQueryResponse,
  DnsServerItem,
} from '../../api/types';
import { useToast } from '../../context/ToastContext';
import { useClipboard } from '../../hooks/useClipboard';
import {
  Globe,
  Wifi,
  WifiOff,
  Radio,
  Search,
  RefreshCw,
  Terminal,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Lock,
  Server,
  Layers,
  ArrowDown,
  ArrowUp,
  Copy,
  Check,
  LayoutGrid,
  List,
  ShieldCheck,
} from 'lucide-react';

type TabType = 'interfaces' | 'wifi' | 'dns' | 'connectivity';
type InterfaceFilterType = 'all' | 'active' | 'physical' | 'bridge' | 'loopback';

interface HealthCheckState {
  status: 'untested' | 'testing' | 'success' | 'error';
  badge: string;
  message: string;
}

export const NetworkPage: React.FC = () => {
  const { addToast } = useToast();

  // Navigation & filtering state
  const [activeTab, setActiveTab] = useState<TabType>('interfaces');
  const [ifaceFilter, setIfaceFilter] = useState<InterfaceFilterType>('all');
  const [ifaceSearch, setIfaceSearch] = useState('');
  const [ifaceViewMode, setIfaceViewMode] = useState<'grid' | 'table'>('grid');

  // Main data state
  const [data, setData] = useState<NetworkSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Copied indicator state for inline visual feedback
  const { copiedKey, copy: copyToClipboard } = useClipboard();

  // WiFi scanning state
  const [wifiScanning, setWifiScanning] = useState(false);
  const [scannedNetworks, setScannedNetworks] = useState<WifiNetworkItem[]>([]);
  const [wifiSearch, setWifiSearch] = useState('');

  // Ping tool state
  const [pingTarget, setPingTarget] = useState('8.8.8.8');
  const [pingCount, setPingCount] = useState<number>(3);
  const [pingLoading, setPingLoading] = useState(false);
  const [pingResult, setPingResult] = useState<PingResponse | null>(null);

  // DNS query tool state
  const [dnsDomain, setDnsDomain] = useState('google.com');
  const [dnsLoading, setDnsLoading] = useState(false);
  const [dnsResult, setDnsResult] = useState<DnsQueryResponse | null>(null);

  // Connectivity Health Checks state
  const [healthChecks, setHealthChecks] = useState<{
    gateway: HealthCheckState;
    dns: HealthCheckState;
    internet: HealthCheckState;
  }>({
    gateway: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to check latency' },
    dns: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to check resolution' },
    internet: { status: 'untested', badge: 'UNTESTED', message: 'Click Test to ping public server' },
  });
  const [healthTestingAll, setHealthTestingAll] = useState(false);

  // Load all network data
  const loadNetwork = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<NetworkSummaryResponse>('/api/network');
      setData(res);

      // Pre-populate scanned networks if wifi info has nearby or networks
      const nearbyNets = res.wifi?.nearby || res.wifi?.networks || [];
      if (nearbyNets.length > 0) {
        setScannedNetworks(nearbyNets);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load network info';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadNetwork();
  }, [loadNetwork]);

  // Copy helper
  const handleCopy = (text: string, key: string, label: string) => {
    if (!text) return;
    copyToClipboard(text, key);
    addToast(`Copied ${label} to clipboard`, 'info');
  };

  // WiFi Scan
  const handleScanWifi = async () => {
    setWifiScanning(true);
    try {
      const res = await api.post<{ networks: WifiNetworkItem[] }>('/api/network/wifi-scan');
      const list = res.networks || [];
      setScannedNetworks(list);
      addToast(`Found ${list.length} wireless networks`, 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'WiFi scan failed';
      addToast(msg, 'error');
    } finally {
      setWifiScanning(false);
    }
  };

  // Ping execution
  const executePing = async (targetToPing: string, countToUse: number) => {
    const cleanTarget = targetToPing.trim();
    if (!cleanTarget) return;

    setPingLoading(true);
    setPingResult(null);

    try {
      const res = await api.get<PingResponse>(
        `/api/network/ping?target=${encodeURIComponent(cleanTarget)}&count=${countToUse}`
      );
      setPingResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ping execution failed';
      addToast(msg, 'error');
    } finally {
      setPingLoading(false);
    }
  };

  const handleRunPing = (e: React.FormEvent) => {
    e.preventDefault();
    executePing(pingTarget, pingCount);
  };

  const handleSetPingPreset = (preset: string) => {
    let resolvedTarget = preset;
    if (preset === 'gateway') {
      resolvedTarget = data?.summary?.default_gateway || '192.168.1.1';
    }
    setPingTarget(resolvedTarget);
    executePing(resolvedTarget, pingCount);
  };

  // DNS Query execution
  const executeDns = async (domainToQuery: string) => {
    const cleanDomain = domainToQuery.trim().toLowerCase();
    if (!cleanDomain) return;

    setDnsLoading(true);
    setDnsResult(null);

    try {
      const res = await api.get<DnsQueryResponse>(
        `/api/network/dns-query?domain=${encodeURIComponent(cleanDomain)}`
      );
      setDnsResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'DNS lookup failed';
      addToast(msg, 'error');
    } finally {
      setDnsLoading(false);
    }
  };

  const handleRunDns = (e: React.FormEvent) => {
    e.preventDefault();
    executeDns(dnsDomain);
  };

  const handleQuickDns = (domain: string) => {
    setDnsDomain(domain);
    executeDns(domain);
  };

  // Connectivity Health Check Probes
  const runGatewayProbe = async (): Promise<void> => {
    const gw = data?.summary?.default_gateway || '192.168.1.1';
    setHealthChecks((prev) => ({
      ...prev,
      gateway: { status: 'testing', badge: 'TESTING...', message: 'Pinging gateway…' },
    }));

    try {
      const res = await api.get<PingResponse>(
        `/api/network/ping?target=${encodeURIComponent(gw)}&count=2`
      );
      if (res.success) {
        const avg = res.avg_latency ?? res.avg_latency_ms;
        setHealthChecks((prev) => ({
          ...prev,
          gateway: {
            status: 'success',
            badge: 'REACHABLE',
            message: `Avg Latency: ${avg !== undefined && avg !== null ? avg.toFixed(1) + ' ms' : 'OK'}`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          gateway: { status: 'error', badge: 'FAILED', message: 'No reply from gateway' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        gateway: { status: 'error', badge: 'FAILED', message: 'Gateway ping request error' },
      }));
    }
  };

  const runDnsProbe = async (): Promise<void> => {
    setHealthChecks((prev) => ({
      ...prev,
      dns: { status: 'testing', badge: 'TESTING...', message: 'Resolving google.com…' },
    }));

    try {
      const res = await api.get<DnsQueryResponse>('/api/network/dns-query?domain=google.com');
      if (res.success) {
        const timeMs = res.time_ms ?? res.latency_ms ?? 0;
        const count = res.count ?? (res.ipv4?.length || 0) + (res.ipv6?.length || 0);
        setHealthChecks((prev) => ({
          ...prev,
          dns: {
            status: 'success',
            badge: 'WORKING',
            message: `Resolved in ${timeMs} ms (${count} answers)`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          dns: { status: 'error', badge: 'FAILED', message: res.error || 'DNS query failed' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        dns: { status: 'error', badge: 'FAILED', message: 'DNS resolution request error' },
      }));
    }
  };

  const runInternetProbe = async (): Promise<void> => {
    setHealthChecks((prev) => ({
      ...prev,
      internet: { status: 'testing', badge: 'TESTING...', message: 'Pinging 1.1.1.1…' },
    }));

    try {
      const res = await api.get<PingResponse>('/api/network/ping?target=1.1.1.1&count=2');
      if (res.success) {
        const avg = res.avg_latency ?? res.avg_latency_ms;
        setHealthChecks((prev) => ({
          ...prev,
          internet: {
            status: 'success',
            badge: 'ONLINE',
            message: `Latency: ${avg !== undefined && avg !== null ? avg.toFixed(1) + ' ms' : 'OK'}`,
          },
        }));
      } else {
        setHealthChecks((prev) => ({
          ...prev,
          internet: { status: 'error', badge: 'OFFLINE', message: 'Could not reach internet' },
        }));
      }
    } catch {
      setHealthChecks((prev) => ({
        ...prev,
        internet: { status: 'error', badge: 'OFFLINE', message: 'Internet ping request error' },
      }));
    }
  };

  const runAllHealthChecks = async () => {
    setHealthTestingAll(true);
    await Promise.allSettled([runGatewayProbe(), runDnsProbe(), runInternetProbe()]);
    setHealthTestingAll(false);
  };

  // Raw data mapping
  const rawInterfaces: NetworkInterfaceItem[] = data?.interfaces || [];
  const summary = data?.summary;
  const wifiInfo = data?.wifi;
  const dnsDetails = data?.dns_details;

  // Filtered interface computation
  const { counts, filteredInterfaces } = useMemo(() => {
    let countActive = 0;
    let countPhysical = 0;
    let countBridge = 0;
    let countLoopback = 0;

    rawInterfaces.forEach((i) => {
      const cat = i.category || i.type || 'ethernet';
      const isUp = i.is_up ?? ((i.state || '').toUpperCase() === 'UP');
      if (isUp) countActive++;
      if (cat === 'wireless' || cat === 'ethernet' || cat === 'cellular') countPhysical++;
      if (cat === 'bridge' || i.name.startsWith('br-') || i.name === 'docker0') countBridge++;
      if (cat === 'loopback' || i.name === 'lo') countLoopback++;
    });

    const filtered = rawInterfaces.filter((i) => {
      const cat = i.category || i.type || 'ethernet';
      const isUp = i.is_up ?? ((i.state || '').toUpperCase() === 'UP');

      if (ifaceFilter === 'active' && !isUp) return false;
      if (
        ifaceFilter === 'physical' &&
        !(cat === 'wireless' || cat === 'ethernet' || cat === 'cellular')
      )
        return false;
      if (
        ifaceFilter === 'bridge' &&
        !(cat === 'bridge' || i.name.startsWith('br-') || i.name === 'docker0')
      )
        return false;
      if (ifaceFilter === 'loopback' && !(cat === 'loopback' || i.name === 'lo')) return false;

      if (ifaceSearch.trim()) {
        const q = ifaceSearch.trim().toLowerCase();
        const matchesName = i.name.toLowerCase().includes(q);
        const matchesMac = (i.mac || '').toLowerCase().includes(q);
        const matchesIp =
          (i.ip || '').toLowerCase().includes(q) ||
          (i.addresses || []).some((a) => a.toLowerCase().includes(q)) ||
          (i.ipv4 || []).some((a) => a.address.toLowerCase().includes(q)) ||
          (i.ipv6 || []).some((a) => a.address.toLowerCase().includes(q));
        if (!matchesName && !matchesMac && !matchesIp) return false;
      }

      return true;
    });

    return {
      counts: {
        all: rawInterfaces.length,
        active: countActive,
        physical: countPhysical,
        bridge: countBridge,
        loopback: countLoopback,
      },
      filteredInterfaces: filtered,
    };
  }, [rawInterfaces, ifaceFilter, ifaceSearch]);

  // WiFi nearby list with search
  const displayWifiNetworks = useMemo(() => {
    let list = scannedNetworks;
    if (list.length === 0 && wifiInfo?.networks && wifiInfo.networks.length > 0) {
      list = wifiInfo.networks;
    }
    if (!wifiSearch.trim()) return list;
    const q = wifiSearch.trim().toLowerCase();
    return list.filter((n) => n.ssid.toLowerCase().includes(q) || (n.bssid || '').toLowerCase().includes(q));
  }, [scannedNetworks, wifiInfo, wifiSearch]);

  // DNS server list normalization
  const dnsServers: DnsServerItem[] = useMemo(() => {
    if (dnsDetails?.servers && dnsDetails.servers.length > 0) {
      return dnsDetails.servers;
    }
    const upstreamIps = dnsDetails?.upstream_ips || data?.dns || [];
    return upstreamIps.map((ip, idx) => ({
      ip,
      provider: ip.startsWith('127.') ? 'Local Stub Resolver' : 'DNS Server',
      is_primary: idx === 0,
      is_stub: ip.startsWith('127.'),
    }));
  }, [dnsDetails, data?.dns]);

  // Interface icon helper
  const renderInterfaceIcon = (cat?: string) => {
    switch (cat) {
      case 'wireless':
        return <Wifi size={18} color="#38bdf8" />;
      case 'bridge':
        return <Layers size={18} color="#a78bfa" />;
      case 'loopback':
        return <RefreshCw size={18} color="#94a3b8" />;
      case 'cellular':
        return <Radio size={18} color="#f59e0b" />;
      default:
        return <Server size={18} color="var(--accent)" />;
    }
  };

  const isOnline = summary?.is_online ?? true;
  const primaryIp = summary?.primary_ip || (rawInterfaces[0]?.ip) || '—';
  const defaultGateway = summary?.default_gateway || 'None';
  const primaryDns = summary?.primary_dns || (dnsServers[0]?.ip) || '—';
  const primaryDnsProvider = summary?.primary_dns_provider || (dnsServers[0]?.provider) || 'Configured DNS';
  const totalRx = summary?.total_rx_fmt || '0 B';
  const totalTx = summary?.total_tx_fmt || '0 B';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Top Header / Toolbar ───────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Globe size={24} color="var(--purple)" />
          <h2 style={{ margin: 0, fontSize: '1.35rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
            Network & WiFi
          </h2>
          <span className="badge badge-lavender">{rawInterfaces.length} Interfaces</span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => loadNetwork(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          title="Refresh complete network state"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Network Summary KPI Cards Bar ──────────────────────── */}
      <div className="net-summary-bar">
        {/* Status Card */}
        <div className="net-metric-card">
          <div className={`net-metric-icon ${isOnline ? 'icon-green' : 'icon-red'}`}>
            {isOnline ? <Wifi size={20} /> : <WifiOff size={20} />}
          </div>
          <div className="net-metric-info">
            <span className="net-metric-label">Status</span>
            <span className="net-metric-value">{isOnline ? 'Online' : 'Disconnected'}</span>
            <span className="net-metric-sub">
              {isOnline
                ? summary?.wifi_connected && summary.wifi_ssid
                  ? `Wi-Fi: ${summary.wifi_ssid}${summary.wifi_signal ? ` (${summary.wifi_signal}%)` : ''}`
                  : `${summary?.primary_type || 'Ethernet'} active`
                : 'No default route'}
            </span>
          </div>
        </div>

        {/* Primary IP Card */}
        <div className="net-metric-card">
          <div className="net-metric-icon icon-cyan">
            <Server size={20} />
          </div>
          <div className="net-metric-info">
            <span className="net-metric-label">Primary IP</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="net-metric-value font-mono">{primaryIp}</span>
              {primaryIp !== '—' && (
                <button
                  className="btn-copy-chip"
                  onClick={() => handleCopy(primaryIp, 'primary-ip', 'Primary IP')}
                  title="Copy IP Address"
                >
                  {copiedKey === 'primary-ip' ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                </button>
              )}
            </div>
            <span className="net-metric-sub">
              {summary?.primary_interface
                ? `${summary.primary_interface} (${summary.primary_type || 'physical'})`
                : 'No interface assigned'}
            </span>
          </div>
        </div>

        {/* Gateway & DNS Card */}
        <div className="net-metric-card">
          <div className="net-metric-icon icon-blue">
            <Globe size={20} />
          </div>
          <div className="net-metric-info">
            <span className="net-metric-label">Gateway & DNS</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span className="net-metric-value font-mono">{defaultGateway}</span>
              {defaultGateway !== 'None' && (
                <button
                  className="btn-copy-chip"
                  onClick={() => handleCopy(defaultGateway, 'gateway-ip', 'Gateway IP')}
                  title="Copy Gateway IP"
                >
                  {copiedKey === 'gateway-ip' ? <Check size={12} color="#34d399" /> : <Copy size={12} />}
                </button>
              )}
            </div>
            <span className="net-metric-sub">
              {primaryDns} · {primaryDnsProvider}
            </span>
          </div>
        </div>

        {/* Total Traffic Card */}
        <div className="net-metric-card">
          <div className="net-metric-icon icon-purple">
            <Activity size={20} />
          </div>
          <div className="net-metric-info">
            <span className="net-metric-label">Total Traffic</span>
            <span className="net-metric-value" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ArrowDown size={14} color="#34d399" /> {totalRx}
            </span>
            <span className="net-metric-sub" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <ArrowUp size={12} color="var(--accent)" /> {totalTx}
            </span>
          </div>
        </div>
      </div>

      {/* ── Tabs Navigation ─────────────────────────────────────── */}
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'interfaces' ? 'active' : ''}`}
          onClick={() => setActiveTab('interfaces')}
        >
          <Server size={15} />
          <span>Interfaces</span>
          <span className="badge badge-lavender" style={{ fontSize: '10px', padding: '1px 6px' }}>
            {rawInterfaces.length}
          </span>
        </button>

        <button
          className={`tab ${activeTab === 'wifi' ? 'active' : ''}`}
          onClick={() => setActiveTab('wifi')}
        >
          <Wifi size={15} />
          <span>WiFi</span>
          {wifiInfo?.connected && wifiInfo.ssid && (
            <span className="badge badge-success iface-wifi-tab-badge" style={{ fontSize: '10px', padding: '1px 6px' }}>
              {wifiInfo.ssid}
            </span>
          )}
        </button>

        <button
          className={`tab ${activeTab === 'dns' ? 'active' : ''}`}
          onClick={() => setActiveTab('dns')}
        >
          <Globe size={15} />
          <span>DNS</span>
          <span className="badge badge-neutral" style={{ fontSize: '10px', padding: '1px 6px' }}>
            {dnsServers.length}
          </span>
        </button>

        <button
          className={`tab ${activeTab === 'connectivity' ? 'active' : ''}`}
          onClick={() => setActiveTab('connectivity')}
        >
          <Activity size={15} />
          <span>Connectivity</span>
        </button>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          TAB 1: INTERFACES
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'interfaces' && (
        <div className="card iface-main-card">
          <div className="card-header iface-card-header">
            <div className="iface-header-title-group">
              <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>Network Interfaces</h3>
              <span className="badge badge-neutral">{filteredInterfaces.length} of {rawInterfaces.length}</span>
            </div>

            <div className="iface-header-controls">
              {/* Search input */}
              <div className="iface-search-wrap">
                <Search
                  size={14}
                  className="iface-search-icon"
                />
                <input
                  type="text"
                  className="form-input iface-search-input"
                  placeholder="Filter interfaces…"
                  value={ifaceSearch}
                  onChange={(e) => setIfaceSearch(e.target.value)}
                />
              </div>

              <div className="iface-header-actions-group">
                {/* View Switcher: Grid vs Table */}
                <div className="iface-view-toggle">
                  <button
                    className={`btn-ghost btn-xs ${ifaceViewMode === 'grid' ? 'active' : ''}`}
                    onClick={() => setIfaceViewMode('grid')}
                    style={{
                      background: ifaceViewMode === 'grid' ? 'var(--accent-dim)' : 'transparent',
                      color: ifaceViewMode === 'grid' ? 'var(--accent)' : 'var(--text-muted)',
                      borderRadius: '4px',
                      padding: '4px 8px',
                    }}
                    title="Card Grid View"
                  >
                    <LayoutGrid size={14} />
                  </button>
                  <button
                    className={`btn-ghost btn-xs ${ifaceViewMode === 'table' ? 'active' : ''}`}
                    onClick={() => setIfaceViewMode('table')}
                    style={{
                      background: ifaceViewMode === 'table' ? 'var(--accent-dim)' : 'transparent',
                      color: ifaceViewMode === 'table' ? 'var(--accent)' : 'var(--text-muted)',
                      borderRadius: '4px',
                      padding: '4px 8px',
                    }}
                    title="Dense Table View"
                  >
                    <List size={14} />
                  </button>
                </div>

                <button
                  className="btn btn-sm btn-secondary iface-refresh-btn"
                  onClick={() => loadNetwork(true)}
                  disabled={loading || refreshing}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
                  title="Refresh interfaces"
                >
                  <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
                  <span>Refresh</span>
                </button>
              </div>
            </div>
          </div>

          <div className="card-body">
            {/* Filter Pills */}
            <div className="iface-filters-row">
              <div className="iface-filters">
                <button
                  className={`iface-filter-btn ${ifaceFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setIfaceFilter('all')}
                >
                  All ({counts.all})
                </button>
                <button
                  className={`iface-filter-btn ${ifaceFilter === 'active' ? 'active' : ''}`}
                  onClick={() => setIfaceFilter('active')}
                >
                  Active ({counts.active})
                </button>
                <button
                  className={`iface-filter-btn ${ifaceFilter === 'physical' ? 'active' : ''}`}
                  onClick={() => setIfaceFilter('physical')}
                >
                  Physical & Wi-Fi ({counts.physical})
                </button>
                <button
                  className={`iface-filter-btn ${ifaceFilter === 'bridge' ? 'active' : ''}`}
                  onClick={() => setIfaceFilter('bridge')}
                >
                  Docker & Bridges ({counts.bridge})
                </button>
                <button
                  className={`iface-filter-btn ${ifaceFilter === 'loopback' ? 'active' : ''}`}
                  onClick={() => setIfaceFilter('loopback')}
                >
                  Loopback ({counts.loopback})
                </button>
              </div>
            </div>

            {loading ? (
              <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px auto' }} />
                <p>Inspecting system network interfaces…</p>
              </div>
            ) : filteredInterfaces.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                <AlertCircle size={28} style={{ margin: '0 auto 8px auto', opacity: 0.6 }} />
                <p>No network interfaces match the current filter "{ifaceFilter}"{ifaceSearch ? ` and query "${ifaceSearch}"` : ''}.</p>
              </div>
            ) : ifaceViewMode === 'grid' ? (
              /* Grid of Cards */
              <div className="interfaces-grid">
                {filteredInterfaces.map((iface) => {
                  const isUp = iface.is_up ?? ((iface.state || '').toUpperCase() === 'UP');
                  const isDefault = iface.is_default;
                  const mac = iface.mac;
                  const mtu = iface.mtu;
                  const speed = iface.speed;
                  const stats = iface.stats;
                  const hasErrors = stats && ((stats.rx_errors || 0) > 0 || (stats.tx_errors || 0) > 0);

                  // Extract all IPv4 and IPv6 addresses
                  const ipv4Addrs = iface.ipv4 && iface.ipv4.length > 0
                    ? iface.ipv4
                    : iface.ip
                    ? [{ address: iface.ip, cidr: iface.ip }]
                    : (iface.addresses || [])
                        .filter((a) => !a.includes(':'))
                        .map((a) => ({ address: a.split('/')[0], cidr: a }));

                  const ipv6Addrs = iface.ipv6 && iface.ipv6.length > 0
                    ? iface.ipv6
                    : (iface.addresses || [])
                        .filter((a) => a.includes(':'))
                        .map((a) => ({ address: a.split('/')[0], cidr: a }));

                  return (
                    <div
                      key={iface.name}
                      className={`iface-card ${isDefault ? 'is-default-route' : ''}`}
                    >
                      {/* Card Header */}
                      <div className="iface-header">
                        <div className="iface-title-wrap">
                          <div className="iface-icon">{renderInterfaceIcon(iface.category || iface.type)}</div>
                          <div className="iface-name-wrap">
                            <h4>{iface.name}</h4>
                          </div>
                        </div>

                        <span className={`badge iface-status-badge ${isUp ? 'status-active' : 'status-inactive'}`}>
                          {iface.state || (isUp ? 'UP' : 'DOWN')}
                        </span>

                        {(isDefault || iface.category || iface.type) && (
                          <div className="iface-badges">
                            {isDefault && <span className="badge-default">DEFAULT</span>}
                            <span className="badge-type">{iface.category || iface.type || 'ethernet'}</span>
                          </div>
                        )}
                      </div>

                      {/* Live RX / TX Stats Bar */}
                      <div className="iface-traffic-bar">
                        <div className="traffic-col">
                          <span className="traffic-icon traffic-rx">↓</span>
                          <span>RX:</span>
                          <span className="traffic-val">{iface.rx_bytes_fmt || '0 B'}</span>
                        </div>
                        <div className="traffic-col">
                          <span className="traffic-icon traffic-tx">↑</span>
                          <span>TX:</span>
                          <span className="traffic-val">{iface.tx_bytes_fmt || '0 B'}</span>
                        </div>
                      </div>

                      {/* Interface Details Grid */}
                      <div className="iface-details">
                        {mac && (
                          <div className="iface-row">
                            <span className="label">MAC Address:</span>
                            <span className="value" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <span>{mac}</span>
                              <button
                                className="btn-copy-chip"
                                onClick={() => handleCopy(mac, `mac-${iface.name}`, 'MAC address')}
                                title="Copy MAC"
                              >
                                {copiedKey === `mac-${iface.name}` ? (
                                  <Check size={11} color="#34d399" />
                                ) : (
                                  <Copy size={11} />
                                )}
                              </button>
                            </span>
                          </div>
                        )}

                        <div className="iface-row">
                          <span className="label">MTU:</span>
                          <span className="value">{mtu || '—'}</span>
                        </div>

                        {speed && (
                          <div className="iface-row">
                            <span className="label">Speed:</span>
                            <span className="value">{speed}</span>
                          </div>
                        )}

                        {stats && (
                          <div className="iface-row">
                            <span className="label">Packets:</span>
                            <span className="value" style={{ fontSize: '11px' }}>
                              ↓ {(stats.rx_packets || 0).toLocaleString()} &nbsp; ↑{' '}
                              {(stats.tx_packets || 0).toLocaleString()}
                            </span>
                          </div>
                        )}

                        {hasErrors && (
                          <div className="iface-row" style={{ color: 'var(--red)' }}>
                            <span className="label" style={{ color: 'var(--red)' }}>Packet Errors:</span>
                            <span className="value" style={{ color: 'var(--red)' }}>
                              RX: {stats?.rx_errors || 0} / TX: {stats?.tx_errors || 0}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* IP Addresses Section */}
                      <div className="addr-section">
                        <span className="label">IP Addresses</span>
                        {ipv4Addrs.length === 0 && ipv6Addrs.length === 0 ? (
                          <span className="text-muted" style={{ fontSize: '11px', fontStyle: 'italic' }}>
                            No assigned addresses
                          </span>
                        ) : (
                          <>
                            {ipv4Addrs.map((a, idx) => (
                              <div key={`ipv4-${idx}`} className="addr-item">
                                <span className="addr-text">{a.cidr}</span>
                                <button
                                  className="btn-copy-chip"
                                  onClick={() => handleCopy(a.address, `addr-v4-${iface.name}-${idx}`, 'IPv4 address')}
                                  title="Copy IPv4"
                                >
                                  {copiedKey === `addr-v4-${iface.name}-${idx}` ? (
                                    <Check size={11} color="#34d399" />
                                  ) : (
                                    <Copy size={11} />
                                  )}
                                </button>
                              </div>
                            ))}

                            {ipv6Addrs.map((a, idx) => (
                              <div key={`ipv6-${idx}`} className="addr-item addr-v6">
                                <span className="addr-text">{a.cidr}</span>
                                <button
                                  className="btn-copy-chip"
                                  onClick={() => handleCopy(a.address, `addr-v6-${iface.name}-${idx}`, 'IPv6 address')}
                                  title="Copy IPv6"
                                >
                                  {copiedKey === `addr-v6-${iface.name}-${idx}` ? (
                                    <Check size={11} color="#a78bfa" />
                                  ) : (
                                    <Copy size={11} />
                                  )}
                                </button>
                              </div>
                            ))}
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* Compact Table View */
              <div className="iface-table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Interface</th>
                      <th>Category</th>
                      <th>State</th>
                      <th>IP Addresses</th>
                      <th>MAC Address</th>
                      <th>Traffic (RX / TX)</th>
                      <th>MTU</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredInterfaces.map((iface) => {
                      const isUp = iface.is_up ?? ((iface.state || '').toUpperCase() === 'UP');
                      const ips = [
                        ...(iface.ipv4?.map((a) => a.cidr) || (iface.ip ? [iface.ip] : [])),
                        ...(iface.ipv6?.map((a) => a.cidr) || []),
                      ];

                      return (
                        <tr key={iface.name}>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              {renderInterfaceIcon(iface.category || iface.type)}
                              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{iface.name}</span>
                              {iface.is_default && <span className="badge-default" style={{ fontSize: '9px' }}>DEFAULT</span>}
                            </div>
                          </td>
                          <td>
                            <span className="badge-type">{iface.category || iface.type || 'ethernet'}</span>
                          </td>
                          <td>
                            <span className={`badge ${isUp ? 'status-active' : 'status-inactive'}`}>
                              {isUp ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                              {iface.state || (isUp ? 'UP' : 'DOWN')}
                            </span>
                          </td>
                          <td>
                            {ips.length > 0 ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                {ips.slice(0, 2).map((ipStr, i) => (
                                  <span key={i} className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                                    {ipStr}
                                  </span>
                                ))}
                                {ips.length > 2 && (
                                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                    +{ips.length - 2} more
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>—</span>
                            )}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {iface.mac || '—'}
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.8rem' }}>
                            <span style={{ color: 'var(--green)' }}>↓ {iface.rx_bytes_fmt || '0 B'}</span>
                            <span style={{ color: 'var(--text-muted)', margin: '0 4px' }}>/</span>
                            <span style={{ color: 'var(--accent)' }}>↑ {iface.tx_bytes_fmt || '0 B'}</span>
                          </td>
                          <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {iface.mtu || '—'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 2: WIFI
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'wifi' && (
        <div className="wifi-tab-container">
          {/* Wireless Hardware Check */}
          {wifiInfo?.has_hardware === false ? (
            <div className="card wifi-disabled-card">
              <div className="wifi-disabled-icon">
                <WifiOff size={28} />
              </div>
              <h3 className="wifi-disabled-title">
                No Wireless Interface Active
              </h3>
              <p className="wifi-disabled-desc">
                {wifiInfo.message || 'No WiFi interfaces found or wireless adapter is currently disabled.'}
              </p>
            </div>
          ) : (
            <div className="wifi-grid">
              {/* 1. Connected Network Hero Card */}
              <div className="wifi-hero-card">
                <div className="wifi-hero-header">
                  <div className="wifi-hero-title">
                    <div className="net-metric-label">
                      Connected Network
                    </div>
                    <h3>
                      <Wifi size={22} color="var(--accent)" className="wifi-hero-icon" />
                      <span className="wifi-hero-ssid">{wifiInfo?.connected && wifiInfo.ssid ? wifiInfo.ssid : 'Not Connected'}</span>
                    </h3>
                  </div>
                  <span className={`badge wifi-hero-status ${wifiInfo?.connected ? 'status-active' : 'status-inactive'}`}>
                    {wifiInfo?.connected ? 'CONNECTED' : 'DISCONNECTED'}
                  </span>
                </div>

                {wifiInfo?.connected ? (
                  <>
                    {/* Signal Meter */}
                    <div className="wifi-signal-meter">
                      <div className="wifi-signal-stat">
                        <span className="wifi-signal-label">SIGNAL</span>
                        <span
                          className={`signal-numeric ${
                            (wifiInfo.signal_percent || 0) >= 65
                              ? 'good'
                              : (wifiInfo.signal_percent || 0) >= 35
                              ? 'warn'
                              : 'crit'
                          }`}
                        >
                          {wifiInfo.signal_percent || 0}%
                        </span>
                      </div>
                      <div className="signal-bar-track">
                        <div
                          className={`signal-bar-fill ${
                            (wifiInfo.signal_percent || 0) >= 65
                              ? 'good'
                              : (wifiInfo.signal_percent || 0) >= 35
                              ? 'warn'
                              : 'crit'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, wifiInfo.signal_percent || 0))}%` }}
                        />
                      </div>
                      <div className="wifi-signal-level">
                        <span className="wifi-signal-label">LEVEL</span>
                        <span className="font-mono wifi-signal-level-val">
                          {wifiInfo.signal_dbm || wifiInfo.quality || '—'}
                        </span>
                      </div>
                    </div>

                    {/* WiFi Specs 4-Box Grid */}
                    <div className="wifi-specs-grid">
                      <div className="wifi-spec-box">
                        <span className="label">Access Point (BSSID)</span>
                        <div className="val wifi-spec-bssid">
                          <span className="wifi-bssid-text">{wifiInfo.bssid || '—'}</span>
                          {wifiInfo.bssid && (
                            <button
                              className="btn-copy-chip"
                              onClick={() => handleCopy(wifiInfo.bssid!, 'wifi-bssid', 'BSSID')}
                              title="Copy BSSID"
                            >
                              {copiedKey === 'wifi-bssid' ? <Check size={11} color="#34d399" /> : <Copy size={11} />}
                            </button>
                          )}
                        </div>
                      </div>

                      <div className="wifi-spec-box">
                        <span className="label">Frequency & Channel</span>
                        <div className="val">
                          {wifiInfo.frequency || '—'} {wifiInfo.channel ? `(Ch ${wifiInfo.channel})` : ''}
                        </div>
                      </div>

                      <div className="wifi-spec-box">
                        <span className="label">Bitrate / Speed</span>
                        <div className="val">{wifiInfo.bitrate || '—'}</div>
                      </div>

                      <div className="wifi-spec-box">
                        <span className="label">Security & Interface</span>
                        <div className="val">
                          {wifiInfo.security || 'WPA2/WPA3'} · {wifiInfo.interface || 'wlan0'}
                        </div>
                      </div>
                    </div>

                    {/* Radio Extra Info Badges */}
                    <div className="wifi-extra-badges">
                      {wifiInfo.mode && (
                        <span className="badge badge-neutral wifi-extra-badge">
                          Mode: {wifiInfo.mode}
                        </span>
                      )}
                      {wifiInfo.tx_power && (
                        <span className="badge badge-neutral wifi-extra-badge">
                          Tx Power: {wifiInfo.tx_power}
                        </span>
                      )}
                      {wifiInfo.driver && (
                        <span className="badge badge-neutral wifi-extra-badge">
                          Driver: {wifiInfo.driver}
                        </span>
                      )}
                      {wifiInfo.rfkill_blocked !== undefined && (
                        <span
                          className={`badge wifi-extra-badge ${wifiInfo.rfkill_blocked ? 'badge-danger' : 'badge-success'}`}
                        >
                          Radio: {wifiInfo.rfkill_blocked ? 'Blocked' : 'Unblocked'}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="wifi-disconnected-note">
                    Device wireless radio is ready on interface <span className="font-mono">{wifiInfo?.interface || 'wlan0'}</span> but not currently connected to an access point.
                  </div>
                )}
              </div>

              {/* 2. Nearby Networks Scanner Card */}
              <div className="card wifi-nearby-card">
                <div className="card-header wifi-scanner-header">
                  <div className="wifi-scanner-title-group">
                    <div className="wifi-scanner-title">
                      <Radio size={18} color="var(--accent)" />
                      <h3>Nearby Wi-Fi Networks</h3>
                    </div>
                    {displayWifiNetworks.length > 0 && (
                      <span className="badge badge-neutral wifi-network-count">
                        {displayWifiNetworks.length} {displayWifiNetworks.length === 1 ? 'network' : 'networks'}
                      </span>
                    )}
                  </div>

                  <div className="wifi-scanner-controls">
                    {/* SSID Filter */}
                    <div className="wifi-search-wrap">
                      <Search size={12} className="wifi-search-icon" />
                      <input
                        type="text"
                        className="form-input wifi-search-input"
                        placeholder="Filter SSID…"
                        value={wifiSearch}
                        onChange={(e) => setWifiSearch(e.target.value)}
                      />
                    </div>

                    <button
                      className="btn btn-sm btn-primary wifi-scan-btn"
                      onClick={handleScanWifi}
                      disabled={wifiScanning}
                    >
                      <RefreshCw size={12} className={wifiScanning ? 'animate-spin' : ''} />
                      <span>{wifiScanning ? 'Scanning airwaves…' : 'Scan Wireless Networks'}</span>
                    </button>
                  </div>
                </div>

                <div className="card-body nearby-table-wrap">
                  {displayWifiNetworks.length === 0 ? (
                    <div className="wifi-scanner-empty">
                      <Radio size={24} className="wifi-empty-icon" />
                      <p>
                        {wifiScanning
                          ? 'Scanning airwaves for broadcast SSIDs…'
                          : 'No WiFi networks scanned yet. Click "Scan Wireless Networks" to search.'}
                      </p>
                    </div>
                  ) : (
                    <table className="nearby-table">
                      <thead>
                        <tr>
                          <th>SSID</th>
                          <th>Signal</th>
                          <th>Channel / Freq</th>
                          <th>Security</th>
                        </tr>
                      </thead>
                      <tbody>
                        {displayWifiNetworks.map((net, idx) => {
                          const isConnected = net.is_current || (wifiInfo?.connected && wifiInfo.ssid === net.ssid);
                          return (
                            <tr key={`${net.ssid}-${net.bssid || idx}`} className={isConnected ? 'current-net' : ''}>
                              <td className="nearby-cell-ssid">
                                <div className="nearby-ssid-wrap">
                                  <strong className="nearby-ssid-name">{net.ssid || '<Hidden Network>'}</strong>
                                  {isConnected && (
                                    <span className="badge status-active nearby-connected-badge">
                                      CONNECTED
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="nearby-cell-signal">
                                <div className="nearby-signal-wrap">
                                  <span className="font-mono nearby-signal-num">{net.signal || 0}%</span>
                                  <div className="progress-bar-outer nearby-signal-bar">
                                    <div
                                      className="progress-bar-inner"
                                      style={{ width: `${Math.min(100, Math.max(0, net.signal || 0))}%` }}
                                    />
                                  </div>
                                </div>
                              </td>
                              <td className="nearby-cell-channel">
                                <span className="nearby-channel-text">
                                  {net.channel ? `Ch ${net.channel}` : ''}{' '}
                                  {net.frequency ? (
                                    <span className="text-muted nearby-freq-text">
                                      ({net.frequency})
                                    </span>
                                  ) : (
                                    ''
                                  )}
                                </span>
                              </td>
                              <td className="nearby-cell-security">
                                <span className="nearby-security-wrap">
                                  <Lock size={11} color="var(--purple)" />
                                  <span className="badge-type">{net.security || 'WPA2/WPA3'}</span>
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 3: DNS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'dns' && (
        <div className="dns-layout">
          {/* Upstream DNS Servers Card */}
          <div className="card">
            <div
              className="card-header"
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Globe size={18} color="var(--blue)" />
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>Upstream DNS Servers</h3>
              </div>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => loadNetwork(true)}
                disabled={loading || refreshing}
              >
                <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
                <span>Refresh</span>
              </button>
            </div>

            <div className="card-body">
              <p className="text-muted" style={{ fontSize: '0.82rem', marginBottom: '14px' }}>
                Active upstream nameservers resolved by the device:
              </p>

              {dnsServers.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No DNS servers detected.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {dnsServers.map((s, idx) => {
                    const isGoogle = s.provider.includes('Google');
                    const isCloudflare = s.provider.includes('Cloudflare');
                    const isQuad9 = s.provider.includes('Quad9');
                    const badgeClass = isGoogle
                      ? 'provider-google'
                      : isCloudflare
                      ? 'provider-cloudflare'
                      : isQuad9
                      ? 'provider-quad9'
                      : '';

                    return (
                      <div key={`dns-srv-${idx}`} className="dns-server-card">
                        <div className="dns-server-left">
                          <div className="iface-icon">
                            <Globe size={16} color="var(--accent)" />
                          </div>
                          <div className="dns-server-info">
                            <div className="dns-ip-row">
                              <span className="dns-ip-text">{s.ip}</span>
                              <button
                                className="btn-copy-chip"
                                onClick={() => handleCopy(s.ip, `dns-ip-${idx}`, 'DNS Server IP')}
                                title="Copy IP"
                              >
                                {copiedKey === `dns-ip-${idx}` ? (
                                  <Check size={11} color="#34d399" />
                                ) : (
                                  <Copy size={11} />
                                )}
                              </button>
                            </div>
                            <div className="dns-badges-row">
                              <span className={`dns-provider-badge ${badgeClass}`}>{s.provider}</span>
                            </div>
                          </div>
                        </div>

                        <div className="dns-server-right">
                          {s.is_primary ? (
                            <span className="badge-default">PRIMARY</span>
                          ) : (
                            <span className="badge-type">SECONDARY</span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Local Stub Note */}
              {dnsDetails?.has_local_stub && (
                <div
                  style={{
                    marginTop: '14px',
                    padding: '10px 12px',
                    background: 'rgba(56, 189, 248, 0.06)',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.8rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.45,
                  }}
                >
                  <strong style={{ color: '#38bdf8' }}>ℹ Systemd-Resolved Stub Active:</strong> Applications query
                  the local stub at <span className="font-mono">127.0.0.53:53</span> which forwards queries upstream
                  to the verified nameservers above.
                </div>
              )}

              {/* Search Domains */}
              {dnsDetails?.search_domains && dnsDetails.search_domains.length > 0 && (
                <div style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>Search Domains: </span>
                  {dnsDetails.search_domains.map((dom, i) => (
                    <span key={i} className="badge badge-neutral" style={{ marginLeft: '4px', fontSize: '10px' }}>
                      {dom}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* DNS Lookup Diagnostic Card */}
          <div className="card">
            <div className="card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Terminal size={18} color="var(--purple)" />
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>DNS Lookup Diagnostic</h3>
              </div>
            </div>

            <div className="card-body">
              <p className="text-muted" style={{ fontSize: '0.82rem', marginBottom: '12px' }}>
                Test domain name resolution against the active system resolvers.
              </p>

              <form onSubmit={handleRunDns} className="diag-input-row">
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. google.com"
                  value={dnsDomain}
                  onChange={(e) => setDnsDomain(e.target.value)}
                  disabled={dnsLoading}
                />
                <button type="submit" className="btn btn-primary" disabled={dnsLoading || !dnsDomain.trim()}>
                  {dnsLoading ? 'Resolving…' : 'Resolve'}
                </button>
              </form>

              {/* Domain Presets */}
              <div className="presets-row">
                <span className="presets-label">Presets:</span>
                {['google.com', 'cloudflare.com', 'github.com', 'kernel.org', 'wikipedia.org'].map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    className="preset-chip"
                    onClick={() => handleQuickDns(preset)}
                  >
                    {preset}
                  </button>
                ))}
              </div>

              {/* Query Result */}
              {dnsResult ? (
                dnsResult.success ? (
                  <div
                    style={{
                      background: 'rgba(16, 185, 129, 0.06)',
                      border: '1px solid rgba(16, 185, 129, 0.3)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px 14px',
                      marginTop: '12px',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        flexWrap: 'wrap',
                        gap: '6px',
                        marginBottom: '10px',
                      }}
                    >
                      <strong style={{ color: 'var(--green)', fontSize: '0.88rem' }}>
                        ✓ Resolved in{' '}
                        <span
                          className={`font-mono ${
                            (dnsResult.time_ms ?? dnsResult.latency_ms ?? 0) < 50
                              ? 'text-green'
                              : (dnsResult.time_ms ?? dnsResult.latency_ms ?? 0) < 150
                              ? 'text-yellow'
                              : 'text-red'
                          }`}
                        >
                          {(dnsResult.time_ms ?? dnsResult.latency_ms ?? 0).toFixed(1)} ms
                        </span>
                      </strong>
                      <span className="badge-type">
                        {dnsResult.count ?? (dnsResult.ipv4?.length || 0) + (dnsResult.ipv6?.length || 0)} answers
                      </span>
                    </div>

                    {/* Single resolved IP fallback */}
                    {dnsResult.resolved_ip && (
                      <div style={{ marginBottom: '8px' }}>
                        <span className="net-metric-label" style={{ display: 'block', marginBottom: '4px' }}>
                          Resolved IP:
                        </span>
                        <div className="addr-badge">{dnsResult.resolved_ip}</div>
                      </div>
                    )}

                    {/* IPv4 Records */}
                    {dnsResult.ipv4 && dnsResult.ipv4.length > 0 && (
                      <div style={{ marginBottom: '8px' }}>
                        <span className="net-metric-label" style={{ display: 'block', marginBottom: '4px' }}>
                          IPv4 Records:
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {dnsResult.ipv4.map((ip, i) => (
                            <span key={i} className="addr-badge">
                              {ip}
                              <button
                                className="btn-copy-chip"
                                style={{ marginLeft: '4px' }}
                                onClick={() => handleCopy(ip, `res-v4-${i}`, 'IPv4')}
                                title="Copy IP"
                              >
                                {copiedKey === `res-v4-${i}` ? <Check size={10} color="#34d399" /> : <Copy size={10} />}
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* IPv6 Records */}
                    {dnsResult.ipv6 && dnsResult.ipv6.length > 0 && (
                      <div>
                        <span className="net-metric-label" style={{ display: 'block', marginBottom: '4px' }}>
                          IPv6 Records:
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                          {dnsResult.ipv6.map((ip, i) => (
                            <span key={i} className="addr-badge addr-badge-v6">
                              {ip}
                              <button
                                className="btn-copy-chip"
                                style={{ marginLeft: '4px' }}
                                onClick={() => handleCopy(ip, `res-v6-${i}`, 'IPv6')}
                                title="Copy IPv6"
                              >
                                {copiedKey === `res-v6-${i}` ? <Check size={10} color="#a78bfa" /> : <Copy size={10} />}
                              </button>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    style={{
                      background: 'rgba(239, 68, 68, 0.08)',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px 14px',
                      marginTop: '12px',
                    }}
                  >
                    <div style={{ color: 'var(--red)', fontWeight: 600, fontSize: '0.88rem' }}>
                      ✗ DNS Resolution Failed
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.82rem', margin: '4px 0 0 0' }}>
                      {dnsResult.error || 'Domain could not be resolved by upstream resolvers.'}
                    </p>
                  </div>
                )
              ) : (
                <div style={{ marginTop: '12px', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Click Resolve to test resolution speed and retrieve A / AAAA records.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 4: CONNECTIVITY & HEALTH
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'connectivity' && (
        <div className="dns-layout connectivity-tab-container">
          {/* Health Checks Probes Card */}
          <div className="card health-checks-card">
            <div className="card-header health-checks-header">
              <div className="health-checks-title-group">
                <ShieldCheck size={18} color="#34d399" />
                <h3 className="health-checks-title">Network Health Checks</h3>
              </div>
              <button
                className="btn btn-sm btn-primary health-test-all-btn"
                onClick={runAllHealthChecks}
                disabled={healthTestingAll}
              >
                <RefreshCw size={12} className={healthTestingAll ? 'animate-spin' : ''} />
                <span>Test All</span>
              </button>
            </div>

            <div className="card-body">
              <div className="health-checks-list">
                {/* 1. Default Gateway Probe */}
                <div className="health-card">
                  <div className="health-card-left">
                    <div className="health-card-icon icon-accent">
                      <Server size={16} />
                    </div>
                    <div className="health-card-info">
                      <div className="health-card-title">
                        <span>Default Gateway</span>
                        <span className="health-card-target health-target-accent">{defaultGateway}</span>
                      </div>
                      <div className="health-card-sub">{healthChecks.gateway.message}</div>
                    </div>
                  </div>
                  <div className="health-card-actions">
                    <span
                      className={`badge ${
                        healthChecks.gateway.status === 'success'
                          ? 'status-active'
                          : healthChecks.gateway.status === 'error'
                          ? 'status-inactive'
                          : 'badge-neutral'
                      }`}
                    >
                      {healthChecks.gateway.badge}
                    </span>
                    <button
                      className="btn btn-xs btn-ghost health-card-test-btn"
                      onClick={runGatewayProbe}
                      disabled={healthChecks.gateway.status === 'testing'}
                    >
                      <RefreshCw size={11} className={healthChecks.gateway.status === 'testing' ? 'animate-spin' : ''} />
                      <span>{healthChecks.gateway.status === 'testing' ? 'Testing…' : 'Test'}</span>
                    </button>
                  </div>
                </div>

                {/* 2. DNS Resolution Probe */}
                <div className="health-card">
                  <div className="health-card-left">
                    <div className="health-card-icon icon-purple">
                      <Globe size={16} />
                    </div>
                    <div className="health-card-info">
                      <div className="health-card-title">
                        <span>DNS Resolution</span>
                        <span className="health-card-target health-target-purple">google.com</span>
                      </div>
                      <div className="health-card-sub">{healthChecks.dns.message}</div>
                    </div>
                  </div>
                  <div className="health-card-actions">
                    <span
                      className={`badge ${
                        healthChecks.dns.status === 'success'
                          ? 'status-active'
                          : healthChecks.dns.status === 'error'
                          ? 'status-inactive'
                          : 'badge-neutral'
                      }`}
                    >
                      {healthChecks.dns.badge}
                    </span>
                    <button
                      className="btn btn-xs btn-ghost health-card-test-btn"
                      onClick={runDnsProbe}
                      disabled={healthChecks.dns.status === 'testing'}
                    >
                      <RefreshCw size={11} className={healthChecks.dns.status === 'testing' ? 'animate-spin' : ''} />
                      <span>{healthChecks.dns.status === 'testing' ? 'Testing…' : 'Test'}</span>
                    </button>
                  </div>
                </div>

                {/* 3. Internet Connectivity Probe */}
                <div className="health-card">
                  <div className="health-card-left">
                    <div className="health-card-icon icon-blue">
                      <Activity size={16} />
                    </div>
                    <div className="health-card-info">
                      <div className="health-card-title">
                        <span>Internet Connectivity</span>
                        <span className="health-card-target health-target-blue">1.1.1.1</span>
                      </div>
                      <div className="health-card-sub">{healthChecks.internet.message}</div>
                    </div>
                  </div>
                  <div className="health-card-actions">
                    <span
                      className={`badge ${
                        healthChecks.internet.status === 'success'
                          ? 'status-active'
                          : healthChecks.internet.status === 'error'
                          ? 'status-inactive'
                          : 'badge-neutral'
                      }`}
                    >
                      {healthChecks.internet.badge}
                    </span>
                    <button
                      className="btn btn-xs btn-ghost health-card-test-btn"
                      onClick={runInternetProbe}
                      disabled={healthChecks.internet.status === 'testing'}
                    >
                      <RefreshCw size={11} className={healthChecks.internet.status === 'testing' ? 'animate-spin' : ''} />
                      <span>{healthChecks.internet.status === 'testing' ? 'Testing…' : 'Test'}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Ping Diagnostic Tool Card */}
          <div className="card ping-diagnostic-card">
            <div className="card-header ping-tool-header">
              <div className="ping-tool-title-group">
                <Activity size={18} color="var(--accent)" />
                <h3 className="ping-tool-title">Ping Diagnostic Tool</h3>
              </div>
            </div>

            <div className="card-body">
              {/* Presets */}
              <div className="presets-row">
                <span className="presets-label">Target Presets:</span>
                <button
                  type="button"
                  className={`preset-chip ${
                    pingTarget === (summary?.default_gateway || '192.168.1.1') || pingTarget === 'gateway'
                      ? 'active'
                      : ''
                  }`}
                  onClick={() => handleSetPingPreset('gateway')}
                >
                  Gateway
                </button>
                <button
                  type="button"
                  className={`preset-chip ${pingTarget === '1.1.1.1' ? 'active' : ''}`}
                  onClick={() => handleSetPingPreset('1.1.1.1')}
                >
                  1.1.1.1 (Cloudflare)
                </button>
                <button
                  type="button"
                  className={`preset-chip ${pingTarget === '8.8.8.8' ? 'active' : ''}`}
                  onClick={() => handleSetPingPreset('8.8.8.8')}
                >
                  8.8.8.8 (Google)
                </button>
                <button
                  type="button"
                  className={`preset-chip ${pingTarget === '9.9.9.9' ? 'active' : ''}`}
                  onClick={() => handleSetPingPreset('9.9.9.9')}
                >
                  9.9.9.9 (Quad9)
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleRunPing} className="ping-controls-wrap">
                <input
                  type="text"
                  className="form-input ping-input"
                  placeholder="IP or Hostname"
                  value={pingTarget}
                  onChange={(e) => setPingTarget(e.target.value)}
                  disabled={pingLoading}
                />
                <div className="ping-controls-actions">
                  <select
                    className="form-input ping-select"
                    value={pingCount}
                    onChange={(e) => setPingCount(parseInt(e.target.value, 10))}
                    disabled={pingLoading}
                  >
                    <option value={2}>2 pkts</option>
                    <option value={3}>3 pkts</option>
                    <option value={5}>5 pkts</option>
                  </select>
                  <button
                    type="submit"
                    className="btn btn-primary ping-submit-btn"
                    disabled={pingLoading || !pingTarget.trim()}
                  >
                    <Activity size={12} className={pingLoading ? 'animate-pulse' : ''} />
                    <span>{pingLoading ? 'Pinging…' : 'Ping'}</span>
                  </button>
                </div>
              </form>

              {/* Ping Result */}
              {pingResult ? (
                pingResult.success ? (
                  <div className="ping-result-card ping-result-success">
                    <div className="ping-result-header">
                      <h4 className="ping-result-title">
                        ✓ Reply from {pingResult.target}
                      </h4>
                      <span
                        className={`badge ${
                          (pingResult.packet_loss ?? pingResult.packet_loss_percent ?? 0) === 0
                            ? 'status-active'
                            : 'status-inactive'
                        }`}
                      >
                        {pingResult.packet_loss ?? pingResult.packet_loss_percent ?? 0}% Loss
                      </span>
                    </div>

                    {/* Stats Boxes Grid */}
                    <div className="ping-results-grid">
                      <div className="ping-stat-box">
                        <div className="label">Avg Latency</div>
                        <div
                          className={`val ${
                            (pingResult.avg_latency ?? pingResult.avg_latency_ms ?? 0) < 50
                              ? 'val-good'
                              : 'val-warn'
                          }`}
                        >
                          {pingResult.avg_latency !== undefined && pingResult.avg_latency !== null
                            ? `${pingResult.avg_latency.toFixed(1)} ms`
                            : pingResult.avg_latency_ms !== undefined && pingResult.avg_latency_ms !== null
                            ? `${pingResult.avg_latency_ms.toFixed(1)} ms`
                            : '—'}
                        </div>
                      </div>

                      <div className="ping-stat-box">
                        <div className="label">Min Latency</div>
                        <div className="val">
                          {pingResult.min_latency !== undefined && pingResult.min_latency !== null
                            ? `${pingResult.min_latency.toFixed(1)} ms`
                            : '—'}
                        </div>
                      </div>

                      <div className="ping-stat-box">
                        <div className="label">Max Latency</div>
                        <div className="val">
                          {pingResult.max_latency !== undefined && pingResult.max_latency !== null
                            ? `${pingResult.max_latency.toFixed(1)} ms`
                            : '—'}
                        </div>
                      </div>

                      <div className="ping-stat-box">
                        <div className="label">Packets</div>
                        <div className="val">
                          {pingResult.received} / {pingResult.transmitted}
                        </div>
                      </div>
                    </div>

                    {/* Collapsible raw output */}
                    {pingResult.output && (
                      <details className="ping-raw-details">
                        <summary className="ping-raw-summary">
                          Raw Output Details
                        </summary>
                        <div className="terminal-box">{pingResult.output}</div>
                      </details>
                    )}
                  </div>
                ) : (
                  <div className="ping-result-card ping-result-error">
                    <h4 className="ping-error-title">
                      ✗ Ping Failed
                    </h4>
                    <p className="ping-error-desc">
                      Could not reach <span className="font-mono">{pingResult.target}</span>.
                    </p>
                    {pingResult.output && (
                      <div className="terminal-box">
                        {pingResult.output}
                      </div>
                    )}
                  </div>
                )
              ) : (
                <div className="ping-empty-state">
                  Enter an IP or choose a preset to test latency and packet loss.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
