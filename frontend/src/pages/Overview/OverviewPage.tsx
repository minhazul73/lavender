import React from 'react';
import { Cpu, Thermometer, Battery, Activity } from 'lucide-react';

export const OverviewPage: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
        }}
      >
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <Cpu size={18} color="var(--purple)" /> CPU Usage
            </span>
            <span className="badge badge-lavender">Realtime</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, margin: '8px 0' }}>
            Telemetry Active
          </div>
          <p style={{ margin: 0, fontSize: '0.82rem' }}>Ready for Phase 3 telemetry stream</p>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <Activity size={18} color="var(--blue)" /> Memory
            </span>
            <span className="badge badge-neutral">RAM</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, margin: '8px 0' }}>
            System Ready
          </div>
          <p style={{ margin: 0, fontSize: '0.82rem' }}>Dynamic memory pressure monitor</p>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <Thermometer size={18} color="var(--yellow)" /> Thermal
            </span>
            <span className="badge badge-warning">Hwmon</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, margin: '8px 0' }}>
            Sensors Active
          </div>
          <p style={{ margin: 0, fontSize: '0.82rem' }}>Thermal zones & fan speeds</p>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <Battery size={18} color="var(--green)" /> Power & Battery
            </span>
            <span className="badge badge-success">OK</span>
          </div>
          <div style={{ fontSize: '1.75rem', fontWeight: 700, margin: '8px 0' }}>
            Online
          </div>
          <p style={{ margin: 0, fontSize: '0.82rem' }}>Supply telemetry & charging rate</p>
        </div>
      </div>
    </div>
  );
};
