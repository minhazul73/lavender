import React, { useMemo } from 'react';
import { Thermometer } from 'lucide-react';
import type { ThermalZone } from '../../api/types';

export interface ThermalCardProps {
  thermal?: any;
  restThermal?: ThermalZone[] | null;
}

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
  if (label.toLowerCase().includes('acpitz')) return 'ACPI System';
  if (label.toLowerCase().includes('composite')) return 'NVMe / SSD';
  if (label.toLowerCase().includes('coretemp')) return 'CPU Core';
  if (label.toLowerCase().includes('hwmon')) return label.replace('hwmon-', 'Sensor ');
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

export const ThermalCard: React.FC<ThermalCardProps> = ({ thermal, restThermal }) => {
  // Thermal zones resolution (live SSE takes precedence, fallback to REST)
  const thermalZones: ThermalZone[] = useMemo(() => {
    if (thermal) {
      if (Array.isArray(thermal)) return thermal;
      if (thermal.zones) return thermal.zones;
    }
    if (restThermal && Array.isArray(restThermal)) return restThermal;
    return [];
  }, [thermal, restThermal]);

  // Priority thermal zones matching live.js & Image 2
  const selectedThermalZones = useMemo(() => {
    if (!thermalZones.length) return [];
    const wanted = ['AOSS (Always-On Sensor)', 'GPU (Adreno)', 'CPU SS0 (Gold/Big)', 'CPU SS1 (LITTLE)'];
    const selected: ThermalZone[] = [];
    thermalZones.forEach((z) => {
      const label = z.display_name || z.name;
      if (wanted.includes(label)) selected.push(z);
    });
    thermalZones.forEach((z) => {
      if (!selected.includes(z) && selected.length < 4) selected.push(z);
    });
    return selected.slice(0, 4);
  }, [thermalZones]);

  return (
    <section className="card card-thermal" style={{ position: 'relative' }}>
      <div className="card-header">
        <div className="card-header-left">
          <span className="card-icon" style={{ background: 'rgba(249,115,22,0.12)', color: 'var(--orange)' }}>
            <Thermometer size={13} />
          </span>
          <span className="card-title">THERMAL</span>
        </div>
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
                <div className="tz-icon">{getZoneIcon('Always-On')}</div>
                <div className="tz-body">
                  <div className="tz-meta">
                    <span className="tz-label">Always-On</span>
                    <span className="tz-badge" style={{ color: '#38bdf8', borderColor: '#38bdf8' }}>
                      42.0°C
                    </span>
                  </div>
                  <div className="tz-track">
                    <div className="tz-fill" style={{ width: '40%', background: 'linear-gradient(90deg, var(--green), #06b6d4)' }} />
                  </div>
                </div>
              </div>
              <div className="tz-row">
                <div className="tz-icon">{getZoneIcon('GPU')}</div>
                <div className="tz-body">
                  <div className="tz-meta">
                    <span className="tz-label">GPU</span>
                    <span className="tz-badge" style={{ color: '#34d399', borderColor: '#34d399' }}>
                      41.5°C
                    </span>
                  </div>
                  <div className="tz-track">
                    <div className="tz-fill" style={{ width: '38%', background: 'linear-gradient(90deg, var(--green), #06b6d4)' }} />
                  </div>
                </div>
              </div>
              <div className="tz-row">
                <div className="tz-icon">{getZoneIcon('CPU Big')}</div>
                <div className="tz-body">
                  <div className="tz-meta">
                    <span className="tz-label">CPU Big</span>
                    <span className="tz-badge" style={{ color: '#fbbf24', borderColor: '#fbbf24' }}>
                      43.8°C
                    </span>
                  </div>
                  <div className="tz-track">
                    <div className="tz-fill" style={{ width: '45%', background: 'linear-gradient(90deg, #f59e0b, #f97316)' }} />
                  </div>
                </div>
              </div>
              <div className="tz-row">
                <div className="tz-icon">{getZoneIcon('CPU Little')}</div>
                <div className="tz-body">
                  <div className="tz-meta">
                    <span className="tz-label">CPU Little</span>
                    <span className="tz-badge" style={{ color: '#34d399', borderColor: '#34d399' }}>
                      42.2°C
                    </span>
                  </div>
                  <div className="tz-track">
                    <div className="tz-fill" style={{ width: '41%', background: 'linear-gradient(90deg, var(--green), #06b6d4)' }} />
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
};
