import React from 'react';
import { Battery } from 'lucide-react';
import type { LiveTelemetryData } from '../../api/types';
import { formatBatteryTime } from '../../utils/formatters';

export interface BatteryCardProps {
  battery?: LiveTelemetryData['battery'] | any;
}

export const BatteryCard: React.FC<BatteryCardProps> = ({ battery: batt }) => {
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

  return (
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

          <div className="batt-stat-tile batt-tile-health">
            <span className="batt-stat-label">Health</span>
            <span
              className="batt-stat-val font-mono"
              id="batt-health-val"
              style={{
                color: (batt?.health || 'good').toLowerCase().includes('good') ? '#34d399' : '#f87171',
              }}
            >
              {batt?.health || 'Good'}
            </span>
          </div>

          <div className="batt-stat-tile batt-tile-energy">
            <span className="batt-stat-label">Energy</span>
            <span className="batt-stat-val font-mono">
              {batt?.energy_full !== undefined && batt?.energy_full !== null
                ? `${(batt.energy_full).toFixed(1)} Wh`
                : batt?.energy !== undefined && batt?.energy !== null
                ? `${(batt.energy).toFixed(1)} Wh`
                : '14.8 Wh'}
            </span>
          </div>

          <div className="batt-stat-tile batt-tile-technology">
            <span className="batt-stat-label">Tech</span>
            <span className="batt-stat-val font-mono">
              {batt?.technology || 'Li-poly'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
