import React from 'react';
import { ShieldCheck, RefreshCw, Server, Globe, Activity } from 'lucide-react';
import type { PingResponse, NetworkSummaryResponse } from '../../api/types';

export interface HealthCheckState {
  status: 'untested' | 'testing' | 'success' | 'error';
  badge: string;
  message: string;
}

export interface ConnectivityTabProps {
  healthChecks: {
    gateway: HealthCheckState;
    dns: HealthCheckState;
    internet: HealthCheckState;
  };
  healthTestingAll: boolean;
  runAllHealthChecks: () => Promise<void>;
  defaultGateway: string;
  runGatewayProbe: () => Promise<void>;
  runDnsProbe: () => Promise<void>;
  runInternetProbe: () => Promise<void>;
  summary?: NetworkSummaryResponse['summary'];
  pingTarget: string;
  setPingTarget: (target: string) => void;
  pingCount: number;
  setPingCount: (count: number) => void;
  pingLoading: boolean;
  pingResult: PingResponse | null;
  handleSetPingPreset: (preset: string) => void;
  handleRunPing: (e: React.FormEvent) => void;
}

export const ConnectivityTab: React.FC<ConnectivityTabProps> = ({
  healthChecks,
  healthTestingAll,
  runAllHealthChecks,
  defaultGateway,
  runGatewayProbe,
  runDnsProbe,
  runInternetProbe,
  summary,
  pingTarget,
  setPingTarget,
  pingCount,
  setPingCount,
  pingLoading,
  pingResult,
  handleSetPingPreset,
  handleRunPing,
}) => {
  return (
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
  );
};
