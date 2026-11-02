import React from 'react';
import {
  Search,
  LayoutGrid,
  List,
  RefreshCw,
  AlertCircle,
  Copy,
  Check,
  CheckCircle2,
  XCircle,
  Wifi,
  Layers,
  Radio,
  Server,
} from 'lucide-react';
import type { NetworkInterfaceItem } from '../../api/types';

export type InterfaceFilterType = 'all' | 'active' | 'physical' | 'bridge' | 'loopback';

export interface InterfacesTabProps {
  filteredInterfaces: NetworkInterfaceItem[];
  rawInterfaces: NetworkInterfaceItem[];
  ifaceSearch: string;
  setIfaceSearch: (search: string) => void;
  ifaceViewMode: 'grid' | 'table';
  setIfaceViewMode: (mode: 'grid' | 'table') => void;
  ifaceFilter: InterfaceFilterType;
  setIfaceFilter: (filter: InterfaceFilterType) => void;
  counts: { all: number; active: number; physical: number; bridge: number; loopback: number };
  loading: boolean;
  refreshing: boolean;
  loadNetwork: (isRefresh?: boolean) => Promise<void>;
  copiedKey: string | null;
  handleCopy: (text: string, key: string, label: string) => void;
}

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

export const InterfacesTab: React.FC<InterfacesTabProps> = ({
  filteredInterfaces,
  rawInterfaces,
  ifaceSearch,
  setIfaceSearch,
  ifaceViewMode,
  setIfaceViewMode,
  ifaceFilter,
  setIfaceFilter,
  counts,
  loading,
  refreshing,
  loadNetwork,
  copiedKey,
  handleCopy,
}) => {
  return (
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
  );
};
