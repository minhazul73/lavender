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
  RefreshCw,
  Activity,
  Server,
  ArrowDown,
  ArrowUp,
  Copy,
  Check,
} from 'lucide-react';
import { InterfacesTab } from './InterfacesTab';
import { WifiTab } from './WifiTab';
import { DnsTab } from './DnsTab';
import { ConnectivityTab, HealthCheckState } from './ConnectivityTab';

type TabType = 'interfaces' | 'wifi' | 'dns' | 'connectivity';
type InterfaceFilterType = 'all' | 'active' | 'physical' | 'bridge' | 'loopback';

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
        <InterfacesTab
          filteredInterfaces={filteredInterfaces}
          rawInterfaces={rawInterfaces}
          ifaceSearch={ifaceSearch}
          setIfaceSearch={setIfaceSearch}
          ifaceViewMode={ifaceViewMode}
          setIfaceViewMode={setIfaceViewMode}
          ifaceFilter={ifaceFilter}
          setIfaceFilter={setIfaceFilter}
          counts={counts}
          loading={loading}
          refreshing={refreshing}
          loadNetwork={loadNetwork}
          copiedKey={copiedKey}
          handleCopy={handleCopy}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 2: WIFI
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'wifi' && (
        <WifiTab
          wifiInfo={wifiInfo}
          displayWifiNetworks={displayWifiNetworks}
          wifiScanning={wifiScanning}
          handleScanWifi={handleScanWifi}
          wifiSearch={wifiSearch}
          setWifiSearch={setWifiSearch}
          copiedKey={copiedKey}
          handleCopy={handleCopy}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 3: DNS
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'dns' && (
        <DnsTab
          dnsServers={dnsServers}
          dnsDetails={dnsDetails}
          loading={loading}
          refreshing={refreshing}
          loadNetwork={loadNetwork}
          dnsDomain={dnsDomain}
          setDnsDomain={setDnsDomain}
          dnsLoading={dnsLoading}
          dnsResult={dnsResult}
          handleRunDns={handleRunDns}
          handleQuickDns={handleQuickDns}
          copiedKey={copiedKey}
          handleCopy={handleCopy}
        />
      )}

      {/* ══════════════════════════════════════════════════════════════
          TAB 4: CONNECTIVITY & HEALTH
         ══════════════════════════════════════════════════════════════ */}
      {activeTab === 'connectivity' && (
        <ConnectivityTab
          healthChecks={healthChecks}
          healthTestingAll={healthTestingAll}
          runAllHealthChecks={runAllHealthChecks}
          defaultGateway={defaultGateway}
          runGatewayProbe={runGatewayProbe}
          runDnsProbe={runDnsProbe}
          runInternetProbe={runInternetProbe}
          summary={summary}
          pingTarget={pingTarget}
          setPingTarget={setPingTarget}
          pingCount={pingCount}
          setPingCount={setPingCount}
          pingLoading={pingLoading}
          pingResult={pingResult}
          handleSetPingPreset={handleSetPingPreset}
          handleRunPing={handleRunPing}
        />
      )}
    </div>
  );
};
