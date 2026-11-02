import React from 'react';
import { Globe, RefreshCw, Terminal, Copy, Check } from 'lucide-react';
import type { DnsServerItem, DnsQueryResponse, NetworkSummaryResponse } from '../../api/types';

export interface DnsTabProps {
  dnsServers: DnsServerItem[];
  dnsDetails?: NetworkSummaryResponse['dns_details'];
  loading: boolean;
  refreshing: boolean;
  loadNetwork: (isRefresh?: boolean) => Promise<void>;
  dnsDomain: string;
  setDnsDomain: (domain: string) => void;
  dnsLoading: boolean;
  dnsResult: DnsQueryResponse | null;
  handleRunDns: (e: React.FormEvent) => void;
  handleQuickDns: (domain: string) => void;
  copiedKey: string | null;
  handleCopy: (text: string, key: string, label: string) => void;
}

export const DnsTab: React.FC<DnsTabProps> = ({
  dnsServers,
  dnsDetails,
  loading,
  refreshing,
  loadNetwork,
  dnsDomain,
  setDnsDomain,
  dnsLoading,
  dnsResult,
  handleRunDns,
  handleQuickDns,
  copiedKey,
  handleCopy,
}) => {
  return (
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
  );
};
