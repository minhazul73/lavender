import React from 'react';
import { Link } from 'react-router-dom';
import { Globe } from 'lucide-react';
import type { LiveTelemetryData } from '../../api/types';
import { formatRate } from '../../utils/formatters';

export interface NetworkCardProps {
  network?: LiveTelemetryData['network'];
  netUpPaths: { area: string; line: string };
  netDownPaths: { area: string; line: string };
}

export const NetworkCard: React.FC<NetworkCardProps> = ({
  network,
  netUpPaths,
  netDownPaths,
}) => {
  const netIface = network?.iface || network?.interface || 'wlan0';
  const netTx = network?.tx_rate_bps ?? network?.tx_rate ?? network?.tx_bytes_sec ?? 11400;
  const netRx = network?.rx_rate_bps ?? network?.rx_rate ?? network?.rx_bytes_sec ?? 2900;

  return (
    <section className="card card-network" style={{ position: 'relative' }}>
      <div className="card-header">
        <span className="card-icon card-icon-net">
          <Globe size={13} />
        </span>
        <span className="card-title">NETWORK TRAFFIC</span>
        <span className="card-subtitle font-mono">—</span>
        <Link to="/network" className="card-link" style={{ marginLeft: 'auto' }}>
          →
        </Link>
      </div>
      <div className="card-body">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <div style={{ display: 'flex', gap: '14px', alignItems: 'baseline' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span style={{ color: 'var(--purple)', fontWeight: 800, fontSize: '15px' }}>↑</span>
              <span className="font-mono" style={{ color: 'var(--purple)', fontWeight: 700, fontSize: '15px' }}>
                {formatRate(netTx)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '2px' }}>Up</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span style={{ color: 'var(--green)', fontWeight: 800, fontSize: '15px' }}>↓</span>
              <span className="font-mono" style={{ color: 'var(--green)', fontWeight: 700, fontSize: '15px' }}>
                {formatRate(netRx)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', marginLeft: '2px' }}>Down</span>
            </div>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }} id="net-iface-middle">
            {netIface}
          </div>
        </div>
        <div className="net-spark-single-wrap">
          <svg className="sparkline sparkline-net sparkline-net-merged" id="sparkline-net-merged" viewBox="0 0 100 40" preserveAspectRatio="none">
            <defs>
              <linearGradient id="grad-net-up" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--purple)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--purple)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="grad-net-down" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--green)" stopOpacity={0.28} />
                <stop offset="100%" stopColor="var(--green)" stopOpacity={0} />
              </linearGradient>
            </defs>
            {/* Upload Curve (Purple) */}
            <path className="sparkline-area" id="sparkarea-net-up" d={netUpPaths.area} fill="url(#grad-net-up)" />
            <path className="sparkline-line" id="sparkpath-net-up" d={netUpPaths.line} strokeWidth={1.2} style={{ stroke: 'var(--purple)' }} />
            {/* Download Curve (Green) */}
            <path className="sparkline-area" id="sparkarea-net-down" d={netDownPaths.area} fill="url(#grad-net-down)" />
            <path className="sparkline-line" id="sparkpath-net-down" d={netDownPaths.line} strokeWidth={1.2} style={{ stroke: 'var(--green)' }} />
          </svg>
        </div>
      </div>
    </section>
  );
};
