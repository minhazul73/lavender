import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Activity } from 'lucide-react';
import { useSmoothSparkline } from '../../hooks/useSmoothSparkline';
import { useOverviewData } from './useOverviewData';
import { CpuCard } from './CpuCard';
import { RamCard } from './RamCard';
import { BatteryCard } from './BatteryCard';
import { StorageCard } from './StorageCard';
import { NetworkCard } from './NetworkCard';
import { ServicesCard } from './ServicesCard';
import { ThermalCard } from './ThermalCard';
import { LogsCard } from './LogsCard';

const MAX_BUF = 30;

export const OverviewPage: React.FC = () => {
  // Historical sparkline buffers
  const [ramHistory, setRamHistory] = useState<number[]>([]);
  const [netUpHistory, setNetUpHistory] = useState<number[]>([]);
  const [netDownHistory, setNetDownHistory] = useState<number[]>([]);
  const [coreBuffers, setCoreBuffers] = useState<Record<number, number[]>>({});

  // Per-metric sparkline buffer updates only when the specific metric updates
  const handleMetricUpdate = useCallback((metric: string, metricData: any) => {
    if (metric === 'ram') {
      if (metricData?.used_pct !== undefined) {
        setRamHistory((prev) => {
          const next = [...prev, metricData.used_pct];
          return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
        });
      }
    } else if (metric === 'network') {
      const tx = metricData?.tx_rate_bps ?? metricData?.tx_rate ?? metricData?.tx_bytes_sec;
      if (tx !== undefined) {
        setNetUpHistory((prev) => {
          const next = [...prev, tx];
          return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
        });
      }
      const rx = metricData?.rx_rate_bps ?? metricData?.rx_rate ?? metricData?.rx_bytes_sec;
      if (rx !== undefined) {
        setNetDownHistory((prev) => {
          const next = [...prev, rx];
          return next.length > MAX_BUF ? next.slice(next.length - MAX_BUF) : next;
        });
      }
    } else if (metric === 'cpu') {
      if (metricData?.per_core_usage && metricData.per_core_usage.length > 0) {
        setCoreBuffers((prev) => {
          const updated = { ...prev };
          metricData.per_core_usage.forEach((c: { core: number; usage?: number | null }) => {
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
    }
  }, []);

  const {
    services,
    disks,
    processes,
    sseData,
    recentLogs,
    restBattery,
    restThermal,
  } = useOverviewData({ onMetric: handleMetricUpdate });
  const liveData = sseData;

  // Seed buffers once from initial telemetry data (e.g. test mocks or first frame)
  const seededRef = useRef(false);
  useEffect(() => {
    if (!seededRef.current && liveData) {
      if (liveData.ram?.used_pct !== undefined && ramHistory.length === 0) {
        setRamHistory([liveData.ram.used_pct]);
      }
      const tx = liveData.network?.tx_rate_bps ?? liveData.network?.tx_rate ?? liveData.network?.tx_bytes_sec;
      if (tx !== undefined && netUpHistory.length === 0) {
        setNetUpHistory([tx]);
      }
      const rx = liveData.network?.rx_rate_bps ?? liveData.network?.rx_rate ?? liveData.network?.rx_bytes_sec;
      if (rx !== undefined && netDownHistory.length === 0) {
        setNetDownHistory([rx]);
      }
      if (liveData.cpu?.per_core_usage && liveData.cpu.per_core_usage.length > 0 && Object.keys(coreBuffers).length === 0) {
        const initialCores: Record<number, number[]> = {};
        liveData.cpu.per_core_usage.forEach((c) => {
          initialCores[c.core] = [c.usage ?? 0];
        });
        setCoreBuffers(initialCores);
      }
      seededRef.current = true;
    }
  }, [liveData, ramHistory.length, netUpHistory.length, netDownHistory.length, coreBuffers]);

  // SVG Catmull-Rom paths for RAM and Network with 60fps rAF smooth interpolation
  const ramPaths = useSmoothSparkline(ramHistory, 100, 32, {
    duration: 650,
    minRange: 15,
    clampMin: 0,
    clampMax: 100,
  });
  const netUpPaths = useSmoothSparkline(netUpHistory, 100, 40, {
    duration: 550,
    minRange: 10240,
    clampMin: 0,
  });
  const netDownPaths = useSmoothSparkline(netDownHistory, 100, 40, {
    duration: 550,
    minRange: 10240,
    clampMin: 0,
  });

  return (
    <div className="overview-dashboard">
      {/* ── Metrics Row: CPU, Memory, Battery, Storage ─────────── */}
      <div className="metrics-row">
        <CpuCard cpu={liveData?.cpu} coreBuffers={coreBuffers} />
        <RamCard ram={liveData?.ram} ramPaths={ramPaths} />
        <BatteryCard battery={liveData?.battery || restBattery} />
        <StorageCard disks={disks} />
      </div>

      {/* ── Middle Row: Network Traffic & Top Processes ──────── */}
      <div className="middle-row">
        <NetworkCard
          network={liveData?.network}
          netUpPaths={netUpPaths}
          netDownPaths={netDownPaths}
        />

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
                    {processes && processes.length > 0 ? (
                      processes.map((p) => {
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
        <ServicesCard services={services} />
        <ThermalCard thermal={liveData?.thermal} restThermal={restThermal} />
        <LogsCard recentLogs={recentLogs} />
      </div>
    </div>
  );
};
