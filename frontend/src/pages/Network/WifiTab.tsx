import React from 'react';
import { Wifi, WifiOff, Radio, Search, RefreshCw, Lock, Copy, Check } from 'lucide-react';
import type { WifiNetworkItem, NetworkSummaryResponse } from '../../api/types';

export interface WifiTabProps {
  wifiInfo?: NetworkSummaryResponse['wifi'];
  displayWifiNetworks: WifiNetworkItem[];
  wifiScanning: boolean;
  handleScanWifi: () => Promise<void>;
  wifiSearch: string;
  setWifiSearch: (search: string) => void;
  copiedKey: string | null;
  handleCopy: (text: string, key: string, label: string) => void;
}

export const WifiTab: React.FC<WifiTabProps> = ({
  wifiInfo,
  displayWifiNetworks,
  wifiScanning,
  handleScanWifi,
  wifiSearch,
  setWifiSearch,
  copiedKey,
  handleCopy,
}) => {
  return (
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
  );
};
