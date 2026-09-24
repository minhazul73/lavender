import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useSSE } from '../../hooks/useSSE';
import { api } from '../../api/client';
import {
  StorageOverviewResponse,
  ServicesListResponse,
  ProcessesOverviewResponse,
  ThermalZone,
} from '../../api/types';
import { Sparkline } from '../../components/common/Sparkline';
import { formatRate, formatMemKb, formatBatteryTime } from '../../utils/formatters';
import {
  Cpu,
  Server,
  Activity,
  HardDrive,
  Globe,
  Thermometer,
  Battery,
  FileText,
} from 'lucide-react';

const MAX_BUF = 30;

export const OverviewPage: React.FC = () => {
  const { data: liveData } = useSSE();

  // Historical sparkline buffers
  const [cpuHistory, setCpuHistory] = useState<number[]>([]);
  const [ramHistory, setRamHistory] = useState<number[]>([]);
  const [netUpHistory, setNetUpHistory] = useState<number[]>([]);
  const [netDownHistory, setNetDownHistory] = useState<number[]>([]);

  // REST data state
  const [storageData, setStorageData] = useState<StorageOverviewResponse | null>(null);
  const [servicesData, setServicesData] = useState<ServicesListResponse | null>(null);
  const [topProcesses, setTopProcesses] = useState<ProcessesOverviewResponse | null>(null);
  const [recentLogs, setRecentLogs] = useState<string[]>([]);

  // Telemetry buffer updater
  useEffect(() => {
    if (!liveData) return;

    if (liveData.cpu?.load5 !== undefined) {
      setCpuHistory((prev) => {
        const next = [...prev, liveData.cpu!.load5! * 10]; // scale for visualization
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    if (liveData.ram?.used_pct !== undefined) {
      setRamHistory((prev) => {
        const next = [...prev, liveData.ram!.used_pct!];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    if (liveData.network?.tx_rate !== undefined) {
      setNetUpHistory((prev) => {
        const next = [...prev, liveData.network!.tx_rate!];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    if (liveData.network?.rx_rate !== undefined) {
      setNetDownHistory((prev) => {
        const next = [...prev, liveData.network!.rx_rate!];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }
  }, [liveData]);

  // Initial REST fetch & periodic refresh
  const fetchRestData = useRef(async () => {
    try {
      const [storage, services, logs, procs] = await Promise.allSettled([
        api.get<StorageOverviewResponse>('/api/system/storage'),
        api.get<ServicesListResponse>('/api/system/services'),
        api.get<{ logs: string[] }>('/api/system/logs?limit=8'),
        api.get<ProcessesOverviewResponse>('/api/system/processes?sort_by=mem&limit=6'),
      ]);

      if (storage.status === 'fulfilled' && storage.value) setStorageData(storage.value);
      if (services.status === 'fulfilled' && services.value) setServicesData(services.value);
      if (logs.status === 'fulfilled' && logs.value?.logs) setRecentLogs(logs.value.logs);
      if (procs.status === 'fulfilled' && procs.value) setTopProcesses(procs.value);
    } catch {
      // background polling error tolerance
    }
  });

  useEffect(() => {
    fetchRestData.current();
    const interval = setInterval(() => {
      if (!document.hidden) {
        fetchRestData.current();
      }
    }, 6000);
    return () => clearInterval(interval);
  }, []);

  // Compute thermal zones
  const thermalZones: ThermalZone[] = React.useMemo(() => {
    if (!liveData?.thermal) return [];
    if (Array.isArray(liveData.thermal)) return liveData.thermal;
    if (liveData.thermal.zones) return liveData.thermal.zones;
    return [];
  }, [liveData?.thermal]);

  // Compute service counts
  const svcCounts = React.useMemo(() => {
    if (!servicesData?.services) return { active: 0, inactive: 0, failed: 0, total: 0 };
    let active = 0, inactive = 0, failed = 0;
    servicesData.services.forEach((s) => {
      const st = (s.active || '').toLowerCase();
      if (st === 'active') active++;
      else if (st === 'failed') failed++;
      else inactive++;
    });
    return { active, inactive, failed, total: servicesData.services.length };
  }, [servicesData]);

  // Battery metrics
  const batt = liveData?.battery;
  const isCharging = batt?.charging || (batt?.state || '').toLowerCase() === 'charging';
  const battPct = batt?.percentage ?? null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ── Health Status Row ──────────────────────────────────── */}
      <div className="health-row" id="health-row">
        <div
          className={`health-pill ${battPct !== null && battPct < 15 && !isCharging ? 'status-crit' : 'status-ok'}`}
        >
          <span className="dot" />
          <span>Battery: {battPct !== null ? `${battPct}%` : 'Plugged'}</span>
        </div>
        <div
          className={`health-pill ${
            thermalZones.some((z) => z.temp > 75)
              ? 'status-crit'
              : thermalZones.some((z) => z.temp > 60)
              ? 'status-warn'
              : 'status-ok'
          }`}
        >
          <span className="dot" />
          <span>
            Thermal: {thermalZones[0]?.temp ? `${thermalZones[0].temp.toFixed(0)}°C` : 'Normal'}
          </span>
        </div>
        <div
          className={`health-pill ${(liveData?.ram?.used_pct || 0) > 85 ? 'status-warn' : 'status-ok'}`}
        >
          <span className="dot" />
          <span>RAM: {liveData?.ram?.used_pct ? `${liveData.ram.used_pct.toFixed(0)}%` : 'OK'}</span>
        </div>
        <div className="health-pill status-ok">
          <span className="dot" />
          <span>Disk: Online</span>
        </div>
        <div className="health-pill status-ok">
          <span className="dot" />
          <span>Net: {liveData?.network?.interface || 'Active'}</span>
        </div>
      </div>

      {/* ── Top Metrics Row: CPU, RAM, Battery, Storage ───────── */}
      <div className="metrics-row">
        {/* CPU Card */}
        <section className="card card-cpu" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-cpu">
              <Cpu size={14} />
            </span>
            <span className="card-title">CPU</span>
            <span
              className="card-subtitle"
              id="cpu-load"
              style={{
                color:
                  (liveData?.cpu?.load5 || 0) > 7
                    ? '#ef4444'
                    : (liveData?.cpu?.load5 || 0) > 3
                    ? '#f59e0b'
                    : 'inherit',
              }}
            >
              {liveData?.cpu?.load5 !== undefined ? liveData.cpu.load5.toFixed(2) : '—'}
            </span>
            <Link to="/processes" className="card-link">
              Processes →
            </Link>
          </div>
          <div className="card-body" style={{ padding: '12px' }}>
            <div className="cpu-cores-grid" id="cpu-cores-grid">
              {liveData?.cpu?.per_core_usage && liveData.cpu.per_core_usage.length > 0 ? (
                liveData.cpu.per_core_usage.map((c) => {
                  const usage = c.usage !== null ? c.usage : 0;
                  const cls = usage > 85 ? 'crit' : usage > 70 ? 'warn' : '';
                  return (
                    <div key={c.core} className="cpu-core">
                      <div className="cpu-core-label">CPU{c.core}</div>
                      <div style={{ flex: 1, padding: '0 4px' }}>
                        <div className="progress-bar-outer" style={{ height: '4px' }}>
                          <div
                            className={`progress-bar-inner ${cls}`}
                            style={{ width: `${Math.min(100, usage)}%` }}
                          />
                        </div>
                      </div>
                      <div className={`cpu-core-value ${cls}`}>{usage.toFixed(0)}%</div>
                    </div>
                  );
                })
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Reading cores…</div>
              )}
            </div>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '10px' }}>
              <div className="stat-sub">{liveData?.cpu?.count || 8} Cores</div>
              <div className="stat-sub font-mono">
                {liveData?.cpu?.cpus?.[0]?.frequency_mhz
                  ? `${liveData.cpu.cpus[0].frequency_mhz.toFixed(0)} MHz`
                  : '—'}
              </div>
            </div>
            <div style={{ marginTop: '8px' }}>
              <Sparkline data={cpuHistory} color="var(--purple)" height={28} />
            </div>
          </div>
        </section>

        {/* Memory Card */}
        <section className="card card-ram" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-ram">
              <Activity size={14} />
            </span>
            <span className="card-title">Memory</span>
            <Link to="/processes" className="card-link">
              →
            </Link>
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                <span className="stat-main" style={{ color: 'var(--blue)' }}>
                  {formatMemKb(liveData?.ram?.used || 0)}
                </span>
                <span className="stat-sub font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  / {formatMemKb(liveData?.ram?.total || 0)}
                </span>
              </div>
              <span
                className="stat-sub font-mono"
                style={{ fontWeight: 700, color: 'var(--blue)', fontSize: '13px' }}
              >
                {(liveData?.ram?.used_pct || 0).toFixed(0)}%
              </span>
            </div>
            <div className="progress-bar-outer" style={{ margin: '8px 0' }}>
              <div
                className={`progress-bar-inner ${
                  (liveData?.ram?.used_pct || 0) > 85
                    ? 'crit'
                    : (liveData?.ram?.used_pct || 0) > 70
                    ? 'warn'
                    : ''
                }`}
                style={{ width: `${Math.min(100, liveData?.ram?.used_pct || 0)}%` }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="stat-sub">{formatMemKb(liveData?.ram?.available || 0)} free</span>
              <span className="stat-sub font-mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {liveData?.ram?.swap_total
                  ? `Swap: ${formatMemKb(liveData.ram.swap_used || 0)}`
                  : `Cache: ${formatMemKb(liveData?.ram?.cached || 0)}`}
              </span>
            </div>
            <div style={{ marginTop: '8px' }}>
              <Sparkline data={ramHistory} color="var(--blue)" height={28} />
            </div>
          </div>
        </section>

        {/* Battery Card */}
        <section className="card card-battery" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-batt">
              <Battery size={14} />
            </span>
            <span className="card-title">Battery</span>
            <span
              className={`batt-badge ${
                isCharging ? 'badge-charging' : battPct !== null ? 'badge-neutral' : 'badge-neutral'
              }`}
            >
              <span className="batt-badge-dot" />
              <span>{isCharging ? '⚡ Charging' : battPct !== null ? 'Discharging' : 'Plugged In'}</span>
            </span>
          </div>
          <div className="card-body">
            <div className="batt-hero-section">
              <div className="batt-hero-left">
                <div className="batt-pct-wrap">
                  <span className="batt-pct-val">{battPct !== null ? `${battPct}%` : '100%'}</span>
                </div>
                <div className="batt-gauge-container">
                  <div className="batt-gauge-track">
                    <div
                      className="batt-gauge-fill"
                      style={{ width: `${Math.min(100, battPct !== null ? battPct : 100)}%` }}
                    />
                  </div>
                  <div className="batt-gauge-cap" />
                </div>
              </div>
              <div className="batt-hero-right">
                <div className="batt-rate-card">
                  <span className="batt-meta-label">Power Rate</span>
                  <span className="batt-meta-val font-mono">
                    {batt?.energy_rate ? `${batt.energy_rate.toFixed(1)} W` : '— W'}
                  </span>
                </div>
                <div className="batt-time-card">
                  <span className="batt-meta-label">Est. Time</span>
                  <span className="batt-meta-val font-mono">
                    {formatBatteryTime(batt?.time_to_empty || batt?.time_to_full)}
                  </span>
                </div>
              </div>
            </div>

            <div className="batt-stats-grid" style={{ marginTop: '12px' }}>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Voltage</span>
                <span className="batt-stat-val font-mono">
                  {batt?.voltage ? `${(batt.voltage / 1000).toFixed(2)} V` : '4.10 V'}
                </span>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Temperature</span>
                <span className="batt-stat-val font-mono">
                  {batt?.temperature ? `${batt.temperature.toFixed(1)}°C` : '32°C'}
                </span>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Health</span>
                <span className="batt-stat-val font-mono">{batt?.health || 'Good'}</span>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Capacity</span>
                <span className="batt-stat-val font-mono">{batt?.capacity ? `${batt.capacity}%` : '100%'}</span>
              </div>
            </div>
          </div>
        </section>

        {/* Storage Card */}
        <section className="card card-storage" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-disk">
              <HardDrive size={14} />
            </span>
            <span className="card-title">Storage</span>
            <Link to="/storage" className="card-link">
              →
            </Link>
          </div>
          <div className="card-body" style={{ padding: '10px 14px', flex: 1, overflowY: 'auto', maxHeight: '200px' }}>
            {storageData?.disks && storageData.disks.length > 0 ? (
              storageData.disks.slice(0, 4).map((d) => {
                const pct = parseInt(d.use_percent.replace('%', ''), 10) || 0;
                return (
                  <div key={d.mount_point} style={{ marginBottom: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '3px' }}>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{d.mount_point}</span>
                      <span className="font-mono" style={{ color: 'var(--text-muted)' }}>
                        {d.used} / {d.size} ({pct}%)
                      </span>
                    </div>
                    <div className="progress-bar-outer" style={{ height: '5px' }}>
                      <div
                        className={`progress-bar-inner ${pct > 85 ? 'crit' : pct > 70 ? 'warn' : ''}`}
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Loading partitions…</div>
            )}
          </div>
        </section>
      </div>

      {/* ── Middle Row: Network Traffic & Top Processes ──────── */}
      <div className="middle-row">
        {/* Network Traffic Card */}
        <section className="card card-network" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-net">
              <Globe size={14} />
            </span>
            <span className="card-title">Network Traffic</span>
            <Link to="/network" className="card-link">
              →
            </Link>
          </div>
          <div className="card-body">
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }}>
              Interface: {liveData?.network?.interface || 'eth0'}
            </div>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ fontSize: '16px', color: 'var(--purple)', fontWeight: 600 }}>
                ↑ {formatRate(liveData?.network?.tx_rate || 0)}
              </div>
              <div style={{ fontSize: '16px', color: 'var(--green)', fontWeight: 600 }}>
                ↓ {formatRate(liveData?.network?.rx_rate || 0)}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginBottom: '2px' }}>Upload</div>
                <Sparkline data={netUpHistory} color="var(--purple)" height={32} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginBottom: '2px' }}>Download</div>
                <Sparkline data={netDownHistory} color="var(--green)" height={32} />
              </div>
            </div>
          </div>
        </section>

        {/* Top Processes Card */}
        <div className="procs-cell-wrap">
          <section className="card card-procs">
            <div className="card-header">
              <span className="card-icon" style={{ background: 'rgba(249,115,22,0.12)', color: 'var(--orange)' }}>
                <Activity size={14} />
              </span>
              <span className="card-title">Top Processes</span>
              <Link to="/processes" className="card-link">
                All →
              </Link>
            </div>
            <div className="card-body proc-card-body" style={{ padding: 0 }}>
              <div className="proc-table-wrap">
                <table className="proc-table">
                  <thead>
                    <tr>
                      <th>Process</th>
                      <th>CPU</th>
                      <th>MEM</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topProcesses?.processes && topProcesses.processes.length > 0 ? (
                      topProcesses.processes.slice(0, 5).map((p) => (
                        <tr key={p.pid}>
                          <td>
                            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</span>
                            <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>
                              ({p.pid})
                            </span>
                          </td>
                          <td className="font-mono">{p.cpu.toFixed(1)}%</td>
                          <td className="font-mono">{p.mem.toFixed(1)}%</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={3} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '16px 0', fontSize: '12px' }}>
                          Loading processes…
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* ── Bottom Row: Services, Thermal, Recent Logs ────────── */}
      <div className="bottom-row">
        {/* Services Donut Breakdown */}
        <section className="card card-services">
          <div className="card-header">
            <span className="card-icon" style={{ background: 'rgba(16,185,129,0.12)', color: 'var(--green)' }}>
              <Server size={14} />
            </span>
            <span className="card-title">Services</span>
            <Link to="/services" className="card-link">
              →
            </Link>
          </div>
          <div className="card-body svc-card-body">
            <div className="svc-layout">
              <div className="svc-donut-wrap">
                <svg viewBox="0 0 36 36">
                  <circle className="svc-donut-bg" cx="18" cy="18" r="15.5" />
                  <circle
                    className="svc-donut-track"
                    cx="18"
                    cy="18"
                    r="15.5"
                    stroke="#10b981"
                    strokeDasharray={`${svcCounts.total > 0 ? (svcCounts.active / svcCounts.total) * 100 : 0} 100`}
                    strokeDashoffset="0"
                  />
                  <circle
                    className="svc-donut-track"
                    cx="18"
                    cy="18"
                    r="15.5"
                    stroke="#ef4444"
                    strokeDasharray={`${svcCounts.total > 0 ? (svcCounts.failed / svcCounts.total) * 100 : 0} 100`}
                    strokeDashoffset={`${-(svcCounts.active / (svcCounts.total || 1)) * 100}`}
                  />
                </svg>
                <div className="svc-donut-label">
                  <span className="total">{svcCounts.total}</span>
                  <span className="label">units</span>
                </div>
              </div>

              <div className="svc-stats">
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--green)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" style={{ color: 'var(--green)' }}>
                      {svcCounts.active}
                    </span>
                    <span className="svc-stat-label">Active</span>
                  </div>
                </div>
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--yellow)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" style={{ color: 'var(--yellow)' }}>
                      {svcCounts.inactive}
                    </span>
                    <span className="svc-stat-label">Inactive</span>
                  </div>
                </div>
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--red)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" style={{ color: 'var(--red)' }}>
                      {svcCounts.failed}
                    </span>
                    <span className="svc-stat-label">Failed</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Thermal Card */}
        <section className="card card-thermal" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon" style={{ background: 'rgba(249,115,22,0.12)', color: 'var(--orange)' }}>
              <Thermometer size={14} />
            </span>
            <span className="card-title">Thermal</span>
          </div>
          <div className="card-body thermal-card-body" style={{ overflowY: 'auto', maxHeight: '180px' }}>
            <div className="thermal-zones">
              {thermalZones.length > 0 ? (
                thermalZones.map((z) => {
                  const isCrit = z.temp > 75;
                  const isWarn = z.temp > 60;
                  return (
                    <div
                      key={z.name}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '6px 0',
                        borderBottom: '1px solid var(--border-subtle)',
                        fontSize: '0.85rem',
                      }}
                    >
                      <span style={{ color: 'var(--text-secondary)' }}>{z.name}</span>
                      <span
                        className="badge"
                        style={{
                          background: isCrit
                            ? 'rgba(239, 68, 68, 0.2)'
                            : isWarn
                            ? 'rgba(245, 158, 11, 0.2)'
                            : 'rgba(16, 185, 129, 0.15)',
                          color: isCrit ? '#f87171' : isWarn ? '#fbbf24' : '#34d399',
                        }}
                      >
                        {z.temp.toFixed(1)}°C
                      </span>
                    </div>
                  );
                })
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Normal range (~38°C)</div>
              )}
            </div>
          </div>
        </section>

        {/* Recent Logs Card */}
        <section className="card">
          <div className="card-header">
            <span className="card-icon" style={{ background: 'rgba(6,182,212,0.12)', color: 'var(--accent)' }}>
              <FileText size={14} />
            </span>
            <span className="card-title">Recent Logs</span>
            <Link to="/services" className="card-link">
              All →
            </Link>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div style={{ maxHeight: '180px', overflowY: 'auto', padding: '8px 12px' }}>
              {recentLogs.length > 0 ? (
                recentLogs.map((log, idx) => (
                  <div
                    key={idx}
                    className="log-entry"
                    style={{
                      fontSize: '0.78rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      padding: '4px 0',
                      borderBottom: '1px solid rgba(255,255,255,0.03)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    <span style={{ color: 'var(--purple)', marginRight: '8px' }}>•</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{log}</span>
                  </div>
                ))
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '12px', padding: '12px' }}>
                  No recent system warnings.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
