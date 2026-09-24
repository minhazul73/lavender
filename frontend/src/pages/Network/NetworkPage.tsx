import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../../api/client';
import {
  NetworkSummaryResponse,
  NetworkInterfaceItem,
  WifiNetworkItem,
  PingResponse,
  DnsQueryResponse,
} from '../../api/types';
import { useToast } from '../../context/ToastContext';
import {
  Globe,
  Wifi,
  Radio,
  Search,
  RefreshCw,
  Terminal,
  Activity,
  CheckCircle2,
  XCircle,
  Lock,
} from 'lucide-react';

export const NetworkPage: React.FC = () => {
  const { addToast } = useToast();
  const [data, setData] = useState<NetworkSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // WiFi scanning state
  const [wifiScanning, setWifiScanning] = useState(false);
  const [scannedNetworks, setScannedNetworks] = useState<WifiNetworkItem[]>([]);

  // Ping tool state
  const [pingTarget, setPingTarget] = useState('1.1.1.1');
  const [pingLoading, setPingLoading] = useState(false);
  const [pingResult, setPingResult] = useState<PingResponse | null>(null);

  // DNS tool state
  const [dnsDomain, setDnsDomain] = useState('google.com');
  const [dnsLoading, setDnsLoading] = useState(false);
  const [dnsResult, setDnsResult] = useState<DnsQueryResponse | null>(null);

  const loadNetwork = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const res = await api.get<NetworkSummaryResponse>('/api/network');
      setData(res);
      if (res.wifi?.networks) {
        setScannedNetworks(res.wifi.networks);
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

  // Trigger WiFi scan
  const handleScanWifi = async () => {
    setWifiScanning(true);
    try {
      const res = await api.post<{ networks: WifiNetworkItem[] }>('/api/network/wifi-scan');
      setScannedNetworks(res.networks || []);
      addToast(`Found ${res.networks?.length || 0} wireless networks`, 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'WiFi scan failed';
      addToast(msg, 'error');
    } finally {
      setWifiScanning(false);
    }
  };

  // Run Ping test
  const handleRunPing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pingTarget.trim()) return;
    setPingLoading(true);
    setPingResult(null);
    try {
      const res = await api.get<PingResponse>(
        `/api/network/ping?target=${encodeURIComponent(pingTarget.trim())}&count=3`
      );
      setPingResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Ping execution failed';
      addToast(msg, 'error');
    } finally {
      setPingLoading(false);
    }
  };

  // Run DNS query test
  const handleRunDns = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!dnsDomain.trim()) return;
    setDnsLoading(true);
    setDnsResult(null);
    try {
      const res = await api.get<DnsQueryResponse>(
        `/api/network/dns-query?domain=${encodeURIComponent(dnsDomain.trim())}`
      );
      setDnsResult(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'DNS lookup failed';
      addToast(msg, 'error');
    } finally {
      setDnsLoading(false);
    }
  };

  const interfaces: NetworkInterfaceItem[] = data?.interfaces || [];
  const wifiInfo = data?.wifi;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Toolbar ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Globe size={22} color="var(--purple)" />
          <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Network Interfaces & Tools</h2>
          <span className="badge badge-lavender">{interfaces.length} Interfaces</span>
        </div>

        <button
          className="btn btn-secondary"
          onClick={() => loadNetwork(true)}
          disabled={loading || refreshing}
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* ── Interface Summary Cards ────────────────────────────── */}
      <div className="card">
        <div className="card-header">
          <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Active Network Interfaces</h3>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Interface</th>
                  <th>IP Address</th>
                  <th>MAC Address</th>
                  <th>State</th>
                  <th>Speed</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      Inspecting interfaces…
                    </td>
                  </tr>
                ) : interfaces.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                      No network interfaces reported.
                    </td>
                  </tr>
                ) : (
                  interfaces.map((iface) => {
                    const isUp = (iface.state || '').toUpperCase() === 'UP';
                    return (
                      <tr key={iface.name}>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{iface.name}</span>
                            {iface.name.startsWith('wl') && <Wifi size={14} color="#38bdf8" />}
                          </div>
                        </td>
                        <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                          {iface.ip || '—'}
                        </td>
                        <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {iface.mac || '—'}
                        </td>
                        <td>
                          <span
                            className={`badge ${isUp ? 'badge-success' : 'badge-warning'}`}
                            style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                          >
                            {isUp ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
                            {iface.state || 'UNKNOWN'}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>{iface.speed || 'Automatic'}</td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Wireless / WiFi Section ────────────────────────────── */}
      <div className="card">
        <div
          className="card-header"
          style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={18} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>WiFi Scanner & Nearby Access Points</h3>
          </div>
          <button
            className="btn btn-sm btn-primary"
            onClick={handleScanWifi}
            disabled={wifiScanning}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <Search size={14} className={wifiScanning ? 'animate-spin' : ''} />
            <span>{wifiScanning ? 'Scanning airwaves…' : 'Scan Wireless Networks'}</span>
          </button>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {wifiInfo?.connected && wifiInfo.ssid && (
            <div
              style={{
                padding: '12px 16px',
                background: 'rgba(56, 189, 248, 0.08)',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                fontSize: '0.88rem',
              }}
            >
              <Wifi size={18} color="#38bdf8" />
              <span>
                Currently connected to <strong style={{ color: '#38bdf8' }}>{wifiInfo.ssid}</strong>{' '}
                {wifiInfo.signal && `(${wifiInfo.signal}%)`}
              </span>
            </div>
          )}

          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>SSID</th>
                  <th>Signal Strength</th>
                  <th>Security</th>
                  <th>Frequency</th>
                </tr>
              </thead>
              <tbody>
                {scannedNetworks.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '24px', color: 'var(--text-muted)' }}>
                      No WiFi networks scanned yet. Click "Scan Wireless Networks" to search.
                    </td>
                  </tr>
                ) : (
                  scannedNetworks.map((net, i) => (
                    <tr key={`${net.ssid}-${i}`}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{net.ssid}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span className="font-mono">{net.signal || 0}%</span>
                          <div className="progress-bar-outer" style={{ width: '80px', height: '4px' }}>
                            <div
                              className="progress-bar-inner"
                              style={{ width: `${Math.min(100, net.signal || 0)}%` }}
                            />
                          </div>
                        </div>
                      </td>
                      <td>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.82rem' }}>
                          <Lock size={12} color="var(--purple)" />
                          {net.security || 'WPA2/WPA3'}
                        </span>
                      </td>
                      <td className="font-mono" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {net.frequency || '2.4 / 5 GHz'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ── Diagnostic Tools: Ping & DNS ──────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
        {/* Ping Tool */}
        <div className="card">
          <div className="card-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="var(--purple)" />
              <h3 style={{ margin: 0, fontSize: '1rem' }}>ICMP Ping Diagnostic</h3>
            </span>
          </div>
          <div className="card-body">
            <form onSubmit={handleRunPing} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <input
                type="text"
                className="form-input"
                placeholder="IP or Host (e.g. 1.1.1.1)"
                value={pingTarget}
                onChange={(e) => setPingTarget(e.target.value)}
                disabled={pingLoading}
              />
              <button type="submit" className="btn btn-primary" disabled={pingLoading}>
                {pingLoading ? 'Pinging…' : 'Ping'}
              </button>
            </form>

            {pingResult && (
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.82rem',
                  fontFamily: "'JetBrains Mono', monospace",
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span>Target: {pingResult.target}</span>
                  <span style={{ color: pingResult.success ? '#34d399' : '#f87171' }}>
                    {pingResult.success ? 'Reachable' : 'Unreachable'}
                  </span>
                </div>
                <div>Transmitted: {pingResult.transmitted} | Received: {pingResult.received}</div>
                <div>Packet Loss: {pingResult.packet_loss}%</div>
                {pingResult.avg_latency_ms !== null && pingResult.avg_latency_ms !== undefined && (
                  <div style={{ color: 'var(--purple)', marginTop: '4px' }}>
                    Avg Latency: {pingResult.avg_latency_ms.toFixed(2)} ms
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* DNS Tool */}
        <div className="card">
          <div className="card-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={18} color="var(--blue)" />
              <h3 style={{ margin: 0, fontSize: '1rem' }}>DNS Resolution Query</h3>
            </span>
          </div>
          <div className="card-body">
            <form onSubmit={handleRunDns} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Domain (e.g. google.com)"
                value={dnsDomain}
                onChange={(e) => setDnsDomain(e.target.value)}
                disabled={dnsLoading}
              />
              <button type="submit" className="btn btn-primary" disabled={dnsLoading}>
                {dnsLoading ? 'Resolving…' : 'Resolve'}
              </button>
            </form>

            {dnsResult && (
              <div
                style={{
                  background: 'rgba(0, 0, 0, 0.4)',
                  padding: '12px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.82rem',
                  fontFamily: "'JetBrains Mono', monospace",
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span>Domain: {dnsResult.domain}</span>
                  <span style={{ color: dnsResult.success ? '#34d399' : '#f87171' }}>
                    {dnsResult.success ? 'Resolved' : 'Failed'}
                  </span>
                </div>
                {dnsResult.resolved_ip && (
                  <div style={{ color: '#38bdf8' }}>IP Address: {dnsResult.resolved_ip}</div>
                )}
                {dnsResult.latency_ms !== null && dnsResult.latency_ms !== undefined && (
                  <div style={{ color: 'var(--text-muted)', marginTop: '4px' }}>
                    Query Time: {dnsResult.latency_ms.toFixed(1)} ms
                  </div>
                )}
                {dnsResult.error && <div style={{ color: '#f87171' }}>Error: {dnsResult.error}</div>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
