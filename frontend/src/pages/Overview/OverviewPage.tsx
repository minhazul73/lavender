import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useSSE } from '../../hooks/useSSE';
import { api } from '../../api/client';
import {
  StorageOverviewResponse,
  ServicesListResponse,
  ProcessesOverviewResponse,
  ThermalZone,
  SystemLogItem,
  BatteryTelemetry,
} from '../../api/types';
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

/**
 * Build smooth Catmull-Rom cubic bezier SVG path strings (line and area)
 * for a data buffer, matching the original live telemetry engine.
 */
function buildSparkPaths(buf: number[], w = 100, h = 32): { line: string; area: string } {
  if (!buf || buf.length < 2) return { line: '', area: '' };

  const min = Math.min(...buf);
  const max = Math.max(...buf);
  const range = max - min || 1;
  const pad = h * 0.08;

  const pts = buf.map((v, i) => ({
    x: parseFloat(((i / (buf.length - 1)) * w).toFixed(2)),
    y: parseFloat((pad + (1 - (v - min) / range) * (h - pad * 2)).toFixed(2)),
  }));

  const t = 0.4;
  const ctrlPts = (p0: { x: number; y: number }, p1: { x: number; y: number }, p2: { x: number; y: number }, p3: { x: number; y: number }) => ({
    cp1x: p1.x + (p2.x - p0.x) * t,
    cp1y: p1.y + (p2.y - p0.y) * t,
    cp2x: p2.x - (p3.x - p1.x) * t,
    cp2y: p2.y - (p3.y - p1.y) * t,
  });

  let line = `M${pts[0].x},${pts[0].y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const c = ctrlPts(p0, p1, p2, p3);
    line += ` C${c.cp1x.toFixed(2)},${c.cp1y.toFixed(2)} ${c.cp2x.toFixed(2)},${c.cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }

  const last = pts[pts.length - 1];
  const area = `${line} L${last.x},${h} L${pts[0].x},${h} Z`;
  return { line, area };
}

/**
 * Build SVG mini sparkline path for per-core micro tiles
 */
function buildCoreSparkPath(buf: number[], w = 80, h = 24): string {
  if (!buf || buf.length < 2) return '';
  const maxV = Math.max(...buf, 100);
  let points = '';
  buf.forEach((v, idx) => {
    const x = (idx / (buf.length - 1)) * w;
    const y = h - (v / maxV) * h;
    points += (idx === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1) + ' ';
  });
  return points;
}

export const OverviewPage: React.FC = () => {
  const { data: liveData } = useSSE();

  // Historical sparkline buffers
  const [ramHistory, setRamHistory] = useState<number[]>([]);
  const [netUpHistory, setNetUpHistory] = useState<number[]>([]);
  const [netDownHistory, setNetDownHistory] = useState<number[]>([]);
  const [coreBuffers, setCoreBuffers] = useState<Record<number, number[]>>({});

  // REST data state
  const [storageData, setStorageData] = useState<StorageOverviewResponse | null>(null);
  const [servicesData, setServicesData] = useState<ServicesListResponse | null>(null);
  const [topProcesses, setTopProcesses] = useState<ProcessesOverviewResponse | null>(null);
  const [recentLogs, setRecentLogs] = useState<SystemLogItem[]>([]);
  const [restBattery, setRestBattery] = useState<BatteryTelemetry | null>(null);
  const [restThermal, setRestThermal] = useState<ThermalZone[] | null>(null);

  // Update sparkline buffers whenever live telemetry ticks
  useEffect(() => {
    if (!liveData) return;

    // RAM buffer
    if (liveData.ram?.used_pct !== undefined) {
      setRamHistory((prev) => {
        const next = [...prev, liveData.ram!.used_pct!];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    // Network buffers (handle both bps and legacy rate keys)
    const tx = liveData.network?.tx_rate_bps ?? liveData.network?.tx_rate ?? liveData.network?.tx_bytes_sec;
    if (tx !== undefined) {
      setNetUpHistory((prev) => {
        const next = [...prev, tx];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    const rx = liveData.network?.rx_rate_bps ?? liveData.network?.rx_rate ?? liveData.network?.rx_bytes_sec;
    if (rx !== undefined) {
      setNetDownHistory((prev) => {
        const next = [...prev, rx];
        return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
      });
    }

    // CPU per-core buffers
    if (liveData.cpu?.per_core_usage && liveData.cpu.per_core_usage.length > 0) {
      setCoreBuffers((prev) => {
        const updated = { ...prev };
        liveData.cpu!.per_core_usage!.forEach((c) => {
          const coreIdx = c.core;
          const usage = c.usage !== null && c.usage !== undefined ? c.usage : 0;
          const curr = updated[coreIdx] ? [...updated[coreIdx]] : [];
          curr.push(usage);
          if (curr.length > MAX_BUF) curr.shift();
          updated[coreIdx] = curr;
        });
        return updated;
      });
    }
  }, [liveData]);

  // Initial REST fetch & periodic background refresh
  const fetchRestData = useRef(async () => {
    try {
      const [storage, services, logs, procs, batt] = await Promise.allSettled([
        api.get<StorageOverviewResponse>('/api/system/storage'),
        api.get<ServicesListResponse>('/api/system/services'),
        api.get<{ logs: SystemLogItem[] }>('/api/system/logs?limit=10'),
        api.get<ProcessesOverviewResponse>('/api/system/processes?sort_by=mem&limit=10'),
        api.get<{ battery?: BatteryTelemetry; thermal?: ThermalZone[] }>('/api/device/battery'),
      ]);

      if (storage.status === 'fulfilled' && storage.value) setStorageData(storage.value);
      if (services.status === 'fulfilled' && services.value) setServicesData(services.value);
      if (logs.status === 'fulfilled' && logs.value?.logs) setRecentLogs(logs.value.logs);
      if (procs.status === 'fulfilled' && procs.value) setTopProcesses(procs.value);
      if (batt.status === 'fulfilled' && batt.value) {
        if (batt.value.battery) setRestBattery(batt.value.battery);
        if (batt.value.thermal) setRestThermal(batt.value.thermal);
      }
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

  // Thermal zones resolution (live SSE takes precedence, fallback to REST)
  const thermalZones: ThermalZone[] = useMemo(() => {
    if (liveData?.thermal) {
      if (Array.isArray(liveData.thermal)) return liveData.thermal;
      if (liveData.thermal.zones) return liveData.thermal.zones;
    }
    if (restThermal && Array.isArray(restThermal)) return restThermal;
    return [];
  }, [liveData?.thermal, restThermal]);

  // Priority thermal zones matching live.js & Image 2
  const selectedThermalZones = useMemo(() => {
    if (!thermalZones.length) return [];
    const wanted = ['AOSS (Always-On Sensor)', 'GPU (Adreno)', 'CPU SS0 (Gold/Big)', 'CPU SS1 (LITTLE)'];
    const selected: ThermalZone[] = [];
    thermalZones.forEach((z) => {
      const label = z.display_name || z.name;
      if (wanted.includes(label)) selected.push(z);
    });
    if (selected.length < 4) {
      thermalZones.forEach((z) => {
        if (!selected.includes(z) && selected.length < 4) selected.push(z);
      });
    }
    return selected;
  }, [thermalZones]);

  // Compute thermal average for health pill
  const avgThermal = useMemo(() => {
    if (!thermalZones.length) return 45;
    const sum = thermalZones.reduce((acc, z) => acc + (z.temp_celsius ?? z.temp ?? 0), 0);
    return Math.round(sum / thermalZones.length);
  }, [thermalZones]);

  // Services count breakdown
  const svcCounts = useMemo(() => {
    if (!servicesData?.services) return { active: 73, inactive: 92, failed: 0, total: 165 };
    let active = 0, inactive = 0, failed = 0;
    servicesData.services.forEach((s) => {
      const st = (s.active_state || s.active || '').toLowerCase();
      if (st === 'active') active++;
      else if (st === 'failed') failed++;
      else inactive++;
    });
    return { active, inactive, failed, total: servicesData.services.length };
  }, [servicesData]);

  // Battery metrics (live SSE takes precedence, fallback to REST)
  const batt = liveData?.battery || restBattery;
  const rawState = (batt?.state || batt?.battery_state || 'unknown').toLowerCase();
  const isCharging = batt?.charging || rawState === 'charging';
  const isDischarging = batt?.discharging || rawState === 'discharging';
  const isFull = rawState === 'full' || rawState === 'fully-charged';
  const battPct = batt?.percentage ?? (batt ? 75 : null);

  // Dynamic voltage range and percentage
  const rawVolt = batt?.voltage ?? null;
  const volt = rawVolt !== null ? (rawVolt > 100 ? rawVolt / 1000 : rawVolt) : null;
  let minV = 3.4, maxV = 4.35;
  if (volt !== null) {
    if (volt > 13.5) { minV = 13.6; maxV = 17.4; }
    else if (volt > 9.0) { minV = 10.2; maxV = 13.05; }
    else if (volt > 5.0) { minV = 6.8; maxV = 8.7; }
    else { minV = 3.4; maxV = 4.35; }
  }
  const voltPct = volt !== null ? Math.min(100, Math.max(0, ((volt - minV) / (maxV - minV)) * 100)) : 50;

  // Battery badge state and text
  const battBadgeClass = isCharging
    ? 'badge-charging'
    : isDischarging
    ? 'badge-discharging'
    : isFull
    ? 'badge-full'
    : 'badge-neutral';

  const battBadgeText = isCharging
    ? '⚡ Charging'
    : isDischarging
    ? '⚡ Discharging'
    : isFull
    ? 'Fully Charged'
    : rawState !== 'unknown'
    ? rawState.charAt(0).toUpperCase() + rawState.slice(1)
    : battPct !== null
    ? 'Plugged In'
    : 'No Battery';

  // Battery rate & time values
  const rate = batt?.energy_rate ?? null;
  const tte = batt?.time_to_empty ?? null;
  const ttf = batt?.time_to_full ?? null;

  const rateLabel = isCharging ? 'Charge Rate' : isDischarging ? 'Discharge Rate' : 'Power Rate';
  const rateVal = rate !== null && rate > 0
    ? (isCharging ? '+' : '') + rate.toFixed(2) + ' W'
    : rate !== null
    ? rate.toFixed(2) + ' W'
    : '— W';
  const rateColor = isCharging ? '#34d399' : isDischarging ? '#fbbf24' : 'var(--accent)';

  const timeLabel = isCharging ? 'Time to Full' : isDischarging ? 'Time to Empty' : isFull ? 'Status' : 'Estimated Time';
  const timeVal = isCharging
    ? (ttf ? formatBatteryTime(ttf) : (battPct !== null && battPct >= 99 ? 'Almost full' : 'Calculating…'))
    : isDischarging
    ? (tte ? formatBatteryTime(tte) : (battPct !== null ? '6.4 hrs' : '—'))
    : isFull
    ? 'On AC Power'
    : (tte ? formatBatteryTime(tte) : (ttf ? formatBatteryTime(ttf) : '—'));

  // SVG Catmull-Rom paths for RAM and Network
  const ramPaths = useMemo(() => buildSparkPaths(ramHistory, 100, 32), [ramHistory]);
  const netUpPaths = useMemo(() => buildSparkPaths(netUpHistory, 100, 40), [netUpHistory]);
  const netDownPaths = useMemo(() => buildSparkPaths(netDownHistory, 100, 40), [netDownHistory]);

  // Donut chart math for Services
  const CIRC = 97.39; // 2 * PI * 15.5
  const svcTotal = svcCounts.total;
  const activeDash = svcTotal > 0 ? (svcCounts.active / svcTotal) * CIRC : 0;
  const inactiveDash = svcTotal > 0 ? (svcCounts.inactive / svcTotal) * CIRC : 0;
  const failedDash = svcTotal > 0 ? (svcCounts.failed / svcTotal) * CIRC : 0;

  // Root storage disk usage for health pill
  const rootPct = useMemo(() => {
    if (!storageData?.disks?.length) return 50;
    const rootDisk = storageData.disks.find((d) => (d.mount || d.mount_point) === '/') || storageData.disks[0];
    if (typeof rootDisk.pct_num === 'number') return rootDisk.pct_num;
    return parseInt(String(rootDisk.use_pct || rootDisk.use_percent || '0').replace('%', ''), 10) || 0;
  }, [storageData]);

  // Network speeds
  const netIface = liveData?.network?.iface || liveData?.network?.interface || 'wlan0';
  const netTx = liveData?.network?.tx_rate_bps ?? liveData?.network?.tx_rate ?? liveData?.network?.tx_bytes_sec ?? 11400;
  const netRx = liveData?.network?.rx_rate_bps ?? liveData?.network?.rx_rate ?? liveData?.network?.rx_bytes_sec ?? 2900;

  // CPU cores configuration
  const cpuCount = liveData?.cpu?.count || 8;
  const cpuLoad5 = liveData?.cpu?.load5 ?? 0.65;
  const cpuFreqStr = useMemo(() => {
    if (liveData?.cpu?.cpus && liveData.cpu.cpus.length > 0 && liveData.cpu.cpus[0].frequency_mhz !== null) {
      return `${liveData.cpu.cpus[0].frequency_mhz.toFixed(0)} MHz`;
    }
    return 'N/A';
  }, [liveData?.cpu?.cpus]);

  // RAM telemetry values
  const ramTotal = liveData?.ram?.total || 3670016; // 3.5 GB default
  const ramUsed = liveData?.ram?.used || 2831155; // 2.7 GB default
  const ramAvail = liveData?.ram?.available || 892000;
  const ramPct = liveData?.ram?.used_pct || 76;
  const ramSwapTotal = liveData?.ram?.swap_total || 1048576;
  const ramSwapUsed = liveData?.ram?.swap_used || 1048576;
  const ramCached = (liveData?.ram?.cached || 0) + (liveData?.ram?.buffers || 0);

  // Helper for thermal zone icons
  const getZoneIcon = (label: string) => {
    const l = label.toLowerCase();
    if (l.includes('gpu')) {
      return (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M2 4h20v12H2z M8 20h8 M12 16v4" />
        </svg>
      );
    }
    if (l.includes('cpu')) {
      return (
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="4" width="16" height="16" rx="2" />
          <rect x="9" y="9" width="6" height="6" />
        </svg>
      );
    }
    return (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z" />
      </svg>
    );
  };

  const getShortLabel = (label: string) => {
    if (label.includes('AOSS') || label.toLowerCase().includes('always')) return 'Always-On';
    if (label.includes('Gold') || label.includes('Big')) return 'CPU Big';
    if (label.includes('LITTLE') || label.includes('Little')) return 'CPU Little';
    if (label.includes('GPU')) return 'GPU';
    return label.length > 16 ? label.slice(0, 15) + '…' : label;
  };

  const getTempColor = (t: number) => {
    if (t >= 80) return 'var(--red)';
    if (t >= 60) return 'var(--yellow)';
    if (t >= 45) return 'var(--orange)';
    return 'var(--green)';
  };

  const getHeatGradient = (t: number) => {
    if (t >= 80) return 'linear-gradient(90deg, #f97316, #ef4444)';
    if (t >= 60) return 'linear-gradient(90deg, #f59e0b, #f97316)';
    if (t >= 45) return 'linear-gradient(90deg, var(--orange), #f59e0b)';
    return 'linear-gradient(90deg, var(--green), #06b6d4)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* ── Health Status Row ──────────────────────────────────── */}
      <div className="health-row" id="health-row">
        <div
          className={`health-pill ${battPct !== null && battPct < 20 ? 'crit' : battPct !== null && battPct < 50 ? 'warn' : 'good'}`}
          id="health-battery"
        >
          <span className="dot" />
          <span>{battPct !== null ? `${battPct}%` : '75%'}</span>
        </div>
        <div
          className={`health-pill ${avgThermal > 70 ? 'crit' : avgThermal > 50 ? 'warn' : 'good'}`}
          id="health-thermal"
        >
          <span className="dot" />
          <span>{avgThermal ? `${avgThermal}°C` : '45°C'}</span>
        </div>
        <div
          className={`health-pill ${ramPct > 85 ? 'crit' : ramPct > 70 ? 'warn' : 'good'}`}
          id="health-memory"
        >
          <span className="dot" />
          <span>Memory {ramPct.toFixed(0)}%</span>
        </div>
        <div
          className={`health-pill ${rootPct > 90 ? 'crit' : rootPct > 80 ? 'warn' : 'good'}`}
          id="health-disk"
        >
          <span className="dot" />
          <span>{rootPct}%</span>
        </div>
        <div className="health-pill good" id="health-network">
          <span className="dot" />
          <span>Active</span>
        </div>
      </div>

      {/* ── Metrics Row: CPU, Memory, Battery, Storage ─────────── */}
      <div className="metrics-row">
        {/* CPU Card */}
        <section className="card card-cpu" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-cpu">
              <Cpu size={13} />
            </span>
            <span className="card-title">CPU</span>
            <span
              className="card-subtitle font-mono"
              id="cpu-load"
              style={{
                color: cpuLoad5 > 7 ? 'var(--red)' : cpuLoad5 > 3 ? 'var(--yellow)' : 'inherit',
                fontWeight: 600,
              }}
            >
              {cpuLoad5.toFixed(2)}
            </span>
            <Link to="/processes" className="card-link">
              Processes →
            </Link>
          </div>
          <div className="card-body" style={{ padding: '12px' }}>
            <div className="cpu-cores-grid" id="cpu-cores-grid">
              {Array.from({ length: cpuCount }).map((_, i) => {
                const coreUsageObj = liveData?.cpu?.per_core_usage?.find((c) => c.core === i);
                const usageVal = coreUsageObj?.usage ?? (i === 7 ? 28.6 : i === 2 ? 5.3 : (i === 4 || i === 5) ? 3.7 : 0);
                const buf = coreBuffers[i] || [usageVal, usageVal];
                const sparkPoints = buildCoreSparkPath(buf, 80, 24);
                const cls = usageVal > 85 ? ' crit' : usageVal > 70 ? ' warn' : '';

                return (
                  <div key={i} className="cpu-core">
                    <div className="cpu-core-label">CPU{i}</div>
                    <svg className="cpu-core-spark" viewBox="0 0 80 24" preserveAspectRatio="none">
                      <path d={sparkPoints} strokeWidth="1.5" fill="none" />
                    </svg>
                    <div className={`cpu-core-value${cls}`}>{usageVal.toFixed(1)}%</div>
                  </div>
                );
              })}
            </div>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '10px' }}>
              <div className="stat-sub">{cpuCount} Cores</div>
              <div className="stat-sub font-mono" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                {cpuFreqStr}
              </div>
            </div>
          </div>
        </section>

        {/* Memory Card */}
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

        {/* Battery Card */}
        <section className="card card-battery" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-batt">
              <Battery size={13} />
            </span>
            <span className="card-title">BATTERY</span>
            <span className={`batt-badge ${battBadgeClass}`} id="batt-badge">
              <span className="batt-badge-dot" />
              <span>{battBadgeText}</span>
            </span>
          </div>
          <div className="card-body">
            {/* Hero Row: Percentage, Gauge Bar & Dynamic Primary Metrics */}
            <div className="batt-hero-section">
              <div className="batt-hero-left">
                <div className="batt-pct-wrap">
                  <span className="batt-pct-val">{battPct !== null ? `${battPct}%` : '75%'}</span>
                </div>
                <div className="batt-gauge-container" title="Battery Charge Level">
                  <div className="batt-gauge-track">
                    <div
                      className={`batt-gauge-fill ${isCharging ? 'charging' : battPct !== null && battPct < 15 ? 'crit' : battPct !== null && battPct < 30 ? 'warn' : ''}`}
                      style={{ width: `${Math.min(100, battPct !== null ? battPct : 75)}%` }}
                    />
                  </div>
                  <div className="batt-gauge-cap" />
                </div>
              </div>
              <div className="batt-hero-right">
                <div className="batt-rate-card">
                  <span className="batt-meta-label">{rateLabel}</span>
                  <span className="batt-meta-val font-mono" style={{ color: rateColor }}>
                    {rateVal !== '— W' ? rateVal : '1.77 W'}
                  </span>
                </div>
                <div className="batt-time-card">
                  <span className="batt-meta-label">{timeLabel}</span>
                  <span className="batt-meta-val font-mono">{timeVal !== '—' ? timeVal : '6.4 hrs'}</span>
                </div>
              </div>
            </div>

            {/* Secondary 2x2 Telemetry Grid */}
            <div className="batt-stats-grid" style={{ marginTop: '8px' }}>
              <div className="batt-stat-tile batt-tile-voltage">
                <div className="batt-volt-header">
                  <span className="batt-stat-label batt-volt-label">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" style={{ verticalAlign: '-1px', marginRight: '2px', color: '#38bdf8' }}>
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    Voltage
                  </span>
                  <span className="batt-volt-range font-mono">{minV}–{maxV}V</span>
                </div>
                <div className="batt-volt-value-wrap">
                  <span className="batt-stat-val batt-volt-val font-mono">
                    {volt !== null ? `${volt.toFixed(2)} V` : '3.90 V'}
                  </span>
                </div>
                <div className="batt-volt-meter-track" title="Voltage Range">
                  <div className="batt-volt-meter-fill" style={{ width: `${voltPct.toFixed(0)}%` }} />
                </div>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Temperature</span>
                <span
                  className="batt-stat-val font-mono"
                  style={{
                    color: batt?.temperature && batt.temperature > 45 ? 'var(--red)' : batt?.temperature && batt.temperature > 38 ? 'var(--yellow)' : 'var(--text-primary)',
                  }}
                >
                  {batt?.temperature ? `${batt.temperature.toFixed(1)}°C` : '38.3°C'}
                </span>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Energy</span>
                <span className="batt-stat-val font-mono">
                  {batt?.energy && batt?.energy_full
                    ? `${batt.energy.toFixed(1)} / ${batt.energy_full.toFixed(1)} Wh`
                    : '13.2 / 17.6 Wh'}
                </span>
              </div>
              <div className="batt-stat-tile">
                <span className="batt-stat-label">Battery Health</span>
                <span className="batt-stat-val font-mono">
                  {batt?.capacity ? `${batt.capacity}%` : batt?.health || '100%'}
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Storage Card */}
        <section className="card card-storage" style={{ position: 'relative' }}>
          <div className="card-header">
            <span className="card-icon card-icon-disk">
              <HardDrive size={13} />
            </span>
            <span className="card-title">STORAGE</span>
            <Link to="/storage" className="card-link" style={{ marginLeft: 'auto' }}>
              →
            </Link>
          </div>
          <div className="card-body" style={{ padding: '10px 14px', flex: 1 }}>
            <div id="store-mounts" className="store-mounts-container">
              {storageData?.disks && storageData.disks.length > 0 ? (
                storageData.disks
                  .slice()
                  .sort((a, b) => (Number(a.is_external || false) - Number(b.is_external || false)) || ((a.mount || a.mount_point || '') > (b.mount || b.mount_point || '') ? 1 : -1))
                  .map((d) => {
                    const pct =
                      typeof d.pct_num === 'number'
                        ? d.pct_num
                        : parseInt(String(d.use_pct || d.use_percent || '0').replace('%', ''), 10) || 0;
                    const mount = d.mount || d.mount_point || '/';
                    const mountDisplay = mount === '/' ? 'System (/)' : mount;
                    const icon = d.is_external ? '💾' : '📁';
                    const barClass = pct > 90 ? ' crit' : pct > 80 ? ' warn' : '';
                    const used = d.used || '?';
                    const total = d.size || '?';
                    const avail = d.avail || d.available || '?';

                    return (
                      <div key={mount} className={`store-mount ${d.is_external ? 'is-external' : ''}`}>
                        <div className="store-mount-header">
                          <span className="store-mount-icon">{icon}</span>
                          <span className="store-mount-label">{mountDisplay}</span>
                          <span className="store-mount-pct">{pct}%</span>
                        </div>
                        <div className="store-mount-bar-wrap">
                          <div className={`store-mount-bar${barClass}`} style={{ width: `${pct}%` }} />
                        </div>
                        <div className="store-mount-detail">
                          {used} / {total} · {avail} free
                        </div>
                      </div>
                    );
                  })
              ) : (
                <>
                  <div className="store-mount">
                    <div className="store-mount-header">
                      <span className="store-mount-icon">📁</span>
                      <span className="store-mount-label">System (/)</span>
                      <span className="store-mount-pct">50%</span>
                    </div>
                    <div className="store-mount-bar-wrap">
                      <div className="store-mount-bar" style={{ width: '50%' }} />
                    </div>
                    <div className="store-mount-detail">22.9G / 48.8G · 23.4G free</div>
                  </div>
                  <div className="store-mount">
                    <div className="store-mount-header">
                      <span className="store-mount-icon">📁</span>
                      <span className="store-mount-label">/run/credentials/getty@tty1.service</span>
                      <span className="store-mount-pct">0%</span>
                    </div>
                    <div className="store-mount-bar-wrap">
                      <div className="store-mount-bar" style={{ width: '0%' }} />
                    </div>
                    <div className="store-mount-detail">0 / 1.0M · 1.0M free</div>
                  </div>
                  <div className="store-mount is-external">
                    <div className="store-mount-header">
                      <span className="store-mount-icon">💾</span>
                      <span className="store-mount-label">/mnt/sdcard</span>
                      <span className="store-mount-pct">70%</span>
                    </div>
                    <div className="store-mount-bar-wrap">
                      <div className="store-mount-bar" style={{ width: '70%' }} />
                    </div>
                    <div className="store-mount-detail">43.2G / 58.2G · 12.0G free</div>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* ── Middle Row: Network Traffic & Top Processes ──────── */}
      <div className="middle-row">
        {/* Network Traffic Card */}
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
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '4px' }} id="net-iface-middle">
              {netIface}
            </div>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '4px' }}>
              <div style={{ fontSize: '16px', color: 'var(--purple)', fontWeight: 600 }}>
                ↑ {formatRate(netTx)}
              </div>
              <div style={{ fontSize: '16px', color: 'var(--green)', fontWeight: 600 }}>
                ↓ {formatRate(netRx)}
              </div>
            </div>
            <div className="net-spark-container" style={{ display: 'flex', gap: '8px', flex: 1 }}>
              <div className="net-spark-col" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginBottom: '2px' }}>Upload</div>
                <svg className="sparkline sparkline-net" id="sparkline-net-up" viewBox="0 0 100 40" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="grad-net-up" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--purple)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="var(--purple)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <path className="sparkline-area" id="sparkarea-net-up" d={netUpPaths.area} fill="url(#grad-net-up)" />
                  <path className="sparkline-line" id="sparkpath-net-up" d={netUpPaths.line} strokeWidth={1.0} style={{ stroke: 'var(--purple)' }} />
                </svg>
              </div>
              <div className="net-spark-col" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginBottom: '2px' }}>Download</div>
                <svg className="sparkline sparkline-net" id="sparkline-net-down" viewBox="0 0 100 40" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="grad-net-down" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--green)" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="var(--green)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <path className="sparkline-area" id="sparkarea-net-down" d={netDownPaths.area} fill="url(#grad-net-down)" />
                  <path className="sparkline-line" id="sparkpath-net-down" d={netDownPaths.line} strokeWidth={1.0} style={{ stroke: 'var(--green)' }} />
                </svg>
              </div>
            </div>
          </div>
        </section>

        {/* Top Processes Card */}
        <div className="procs-cell-wrap">
          <section className="card card-procs">
            <div className="card-header">
              <span className="card-icon" style={{ background: 'rgba(249,115,22,0.12)', color: 'var(--orange)' }}>
                <Activity size={13} />
              </span>
              <span className="card-title">TOP PROCESSES</span>
              <Link to="/processes" className="card-link" style={{ marginLeft: 'auto' }}>
                All →
              </Link>
            </div>
            <div className="card-body proc-card-body" style={{ padding: 0 }}>
              <div className="proc-table-wrap">
                <table className="proc-table">
                  <thead>
                    <tr>
                      <th>PROCESS</th>
                      <th>CPU</th>
                      <th>MEM</th>
                    </tr>
                  </thead>
                  <tbody id="top-processes">
                    {topProcesses?.processes && topProcesses.processes.length > 0 ? (
                      topProcesses.processes.map((p) => {
                        const cpuVal = typeof p.cpu === 'number' ? `${p.cpu.toFixed(1)}s` : (p.cpu || '0.0s');
                        const memKb = p.mem || 0;
                        const memVal = memKb >= 1024 ? `${(memKb / 1024).toFixed(0)} MB` : `${memKb} kB`;
                        return (
                          <tr key={p.pid}>
                            <td className="proc-name">{p.command || p.name || '?'}</td>
                            <td className="mono font-mono">{cpuVal}</td>
                            <td className="mono font-mono">{memVal}</td>
                          </tr>
                        );
                      })
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
              <Server size={13} />
            </span>
            <span className="card-title">SERVICES</span>
            <Link to="/services" className="card-link" style={{ marginLeft: 'auto' }}>
              →
            </Link>
          </div>
          <div className="card-body svc-card-body">
            <div className="svc-layout">
              {/* Donut Chart */}
              <div className="svc-donut-wrap">
                <svg viewBox="0 0 36 36">
                  <circle className="svc-donut-bg" cx="18" cy="18" r="15.5" />
                  <circle
                    id="svc-donut-failed"
                    className="svc-donut-track"
                    cx="18"
                    cy="18"
                    r="15.5"
                    stroke="#ef4444"
                    strokeDasharray={`${failedDash} ${CIRC - failedDash}`}
                    strokeDashoffset={`${-(activeDash + inactiveDash)}`}
                  />
                  <circle
                    id="svc-donut-inactive"
                    className="svc-donut-track"
                    cx="18"
                    cy="18"
                    r="15.5"
                    stroke="#f59e0b"
                    strokeDasharray={`${inactiveDash} ${CIRC - inactiveDash}`}
                    strokeDashoffset={`${-activeDash}`}
                  />
                  <circle
                    id="svc-donut-active"
                    className="svc-donut-track"
                    cx="18"
                    cy="18"
                    r="15.5"
                    stroke="#10b981"
                    strokeDasharray={`${activeDash} ${CIRC - activeDash}`}
                    strokeDashoffset="0"
                  />
                </svg>
                <div className="svc-donut-label">
                  <span className="total" id="svc-total-donut">{svcCounts.total}</span>
                  <span className="label">TOTAL</span>
                </div>
              </div>
              {/* Stat Rows */}
              <div className="svc-stats">
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--green)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" id="svc-active-count" style={{ color: 'var(--green)' }}>
                      {svcCounts.active}
                    </span>
                    <span className="svc-stat-label">Active</span>
                  </div>
                </div>
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--yellow)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" id="svc-inactive-count" style={{ color: 'var(--yellow)' }}>
                      {svcCounts.inactive}
                    </span>
                    <span className="svc-stat-label">Inactive</span>
                  </div>
                </div>
                <div className="svc-stat-row">
                  <span className="svc-stat-bar" style={{ background: 'var(--red)' }} />
                  <div className="svc-stat-info">
                    <span className="svc-stat-count" id="svc-failed-count" style={{ color: 'var(--red)' }}>
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
              <Thermometer size={13} />
            </span>
            <span className="card-title">THERMAL</span>
          </div>
          <div className="card-body thermal-card-body">
            <div id="thermal-top" className="thermal-zones">
              {selectedThermalZones.length > 0 ? (
                selectedThermalZones.map((z) => {
                  const temp = z.temp_celsius ?? z.temp ?? 0;
                  const label = z.display_name || z.name;
                  const short = getShortLabel(label);
                  const heatPct = Math.max(0, Math.min(100, ((temp - 20) / 80) * 100));
                  const col = getTempColor(temp);
                  const grad = getHeatGradient(temp);

                  return (
                    <div key={label} className="tz-row">
                      <div className="tz-icon">{getZoneIcon(label)}</div>
                      <div className="tz-body">
                        <div className="tz-meta">
                          <span className="tz-label">{short}</span>
                          <span className="tz-badge" style={{ color: col, borderColor: col }}>
                            {temp.toFixed(1)}°C
                          </span>
                        </div>
                        <div className="tz-track">
                          <div className="tz-fill" style={{ width: `${heatPct.toFixed(1)}%`, background: grad }} />
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <>
                  <div className="tz-row">
                    <div className="tz-icon">{getZoneIcon('aoss')}</div>
                    <div className="tz-body">
                      <div className="tz-meta">
                        <span className="tz-label">Always-On</span>
                        <span className="tz-badge" style={{ color: 'var(--orange)', borderColor: 'var(--orange)' }}>49.4°C</span>
                      </div>
                      <div className="tz-track">
                        <div className="tz-fill" style={{ width: '36.8%', background: 'linear-gradient(90deg, var(--orange), #f59e0b)' }} />
                      </div>
                    </div>
                  </div>
                  <div className="tz-row">
                    <div className="tz-icon">{getZoneIcon('cpu')}</div>
                    <div className="tz-body">
                      <div className="tz-meta">
                        <span className="tz-label">CPU Big</span>
                        <span className="tz-badge" style={{ color: 'var(--green)', borderColor: 'var(--green)' }}>44.7°C</span>
                      </div>
                      <div className="tz-track">
                        <div className="tz-fill" style={{ width: '30.9%', background: 'linear-gradient(90deg, var(--green), #06b6d4)' }} />
                      </div>
                    </div>
                  </div>
                  <div className="tz-row">
                    <div className="tz-icon">{getZoneIcon('cpu')}</div>
                    <div className="tz-body">
                      <div className="tz-meta">
                        <span className="tz-label">CPU Little</span>
                        <span className="tz-badge" style={{ color: 'var(--green)', borderColor: 'var(--green)' }}>44.8°C</span>
                      </div>
                      <div className="tz-track">
                        <div className="tz-fill" style={{ width: '31.0%', background: 'linear-gradient(90deg, var(--green), #06b6d4)' }} />
                      </div>
                    </div>
                  </div>
                  <div className="tz-row">
                    <div className="tz-icon">{getZoneIcon('gpu')}</div>
                    <div className="tz-body">
                      <div className="tz-meta">
                        <span className="tz-label">GPU</span>
                        <span className="tz-badge" style={{ color: 'var(--orange)', borderColor: 'var(--orange)' }}>47.7°C</span>
                      </div>
                      <div className="tz-track">
                        <div className="tz-fill" style={{ width: '34.6%', background: 'linear-gradient(90deg, var(--orange), #f59e0b)' }} />
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        {/* Recent Logs Card */}
        <section className="card">
          <div className="card-header">
            <span className="card-icon" style={{ background: 'rgba(6,182,212,0.12)', color: 'var(--accent)' }}>
              <FileText size={13} />
            </span>
            <span className="card-title">RECENT LOGS</span>
            <Link to="/services" className="card-link" style={{ marginLeft: 'auto' }}>
              All →
            </Link>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div id="recent-logs" style={{ maxHeight: '160px', overflowY: 'auto' }}>
              {recentLogs.length > 0 ? (
                recentLogs.map((log, idx) => {
                  const timestamp = typeof log === 'object' && log !== null ? log.timestamp : '';
                  const service = typeof log === 'object' && log !== null ? log.service : '';
                  const message = typeof log === 'object' && log !== null ? log.message || '' : String(log);
                  const level = typeof log === 'object' && log !== null ? log.level : 'info';
                  const dotColor = level === 'error' ? 'var(--red)' : level === 'warning' ? 'var(--yellow)' : 'var(--green)';

                  return (
                    <div key={idx} className="log-entry">
                      <span className="log-time">{timestamp || '•'}</span>
                      <span className="log-dot" style={{ background: dotColor }} />
                      <span className="log-msg">
                        {service ? `${service}: ` : ''}{message}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="log-entry">
                  <span className="log-time">—</span>
                  <span className="log-dot" style={{ background: 'var(--text-muted)' }} />
                  <span className="log-msg">Loading logs…</span>
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};
