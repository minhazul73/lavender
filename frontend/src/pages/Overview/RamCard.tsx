import React from 'react';
import { Link } from 'react-router-dom';
import { Activity } from 'lucide-react';
import type { LiveTelemetryData } from '../../api/types';
import { formatMemKb } from '../../utils/formatters';

export interface RamCardProps {
  ram?: LiveTelemetryData['ram'];
  ramPaths: { area: string; line: string };
}

export const RamCard: React.FC<RamCardProps> = ({ ram, ramPaths }) => {
  const ramTotal = ram?.total || 3670016; // 3.5 GB default
  const ramUsed = ram?.used || 2831155; // 2.7 GB default
  const ramAvail = ram?.available || 892000;
  const ramPct = ram?.used_pct || 76;
  const ramSwapTotal = ram?.swap_total || 1048576;
  const ramSwapUsed = ram?.swap_used || 1048576;
  const ramCached = (ram?.cached || 0) + (ram?.buffers || 0);

  return (
    <section className="card card-ram" style={{ position: 'relative' }}>
      <div className="card-header">
        <span className="card-icon card-icon-ram">
          <Activity size={13} />
        </span>
        <span className="card-title">MEMORY</span>
        <span className="card-subtitle font-mono">—</span>
        <Link to="/processes" className="card-link" style={{ marginLeft: 'auto' }}>
          →
        </Link>
      </div>
      <div className="card-body">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '3px' }}>
            <span className="stat-main" style={{ color: 'var(--blue)' }}>
              {formatMemKb(ramUsed)}
            </span>
            <span className="stat-sub font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              / {formatMemKb(ramTotal)}
            </span>
          </div>
          <span
            className="stat-sub font-mono"
            style={{ fontWeight: 700, color: 'var(--blue)', fontSize: '13px' }}
          >
            {ramPct.toFixed(0)}%
          </span>
        </div>
        <div className="progress-bar-outer" style={{ margin: '8px 0' }}>
          <div
            className={`progress-bar-inner ${ramPct > 85 ? 'crit' : ramPct > 70 ? 'warn' : ''}`}
            style={{ width: `${Math.min(100, ramPct)}%` }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span className="stat-sub">{formatMemKb(ramAvail)} free</span>
          <span className="stat-sub font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {ramSwapTotal > 0 ? `Swap: ${formatMemKb(ramSwapUsed)}` : `Cache: ${formatMemKb(ramCached)}`}
          </span>
        </div>
        <svg className="sparkline" id="sparkline-ram" viewBox="0 0 100 32" preserveAspectRatio="none">
          <defs>
            <linearGradient id="grad-ram" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--blue)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="var(--blue)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <path className="sparkline-area" d={ramPaths.area} fill="url(#grad-ram)" />
          <path className="sparkline-line" d={ramPaths.line} strokeWidth={1.2} />
        </svg>
      </div>
    </section>
  );
};
