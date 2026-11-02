import React from 'react';
import { RotateCw, Power, Moon } from 'lucide-react';
import type { PowerStateResponse } from '../../api/types';

export interface PowerActionsCardProps {
  onReboot: () => void;
  onPoweroff: () => void;
  onSuspend: () => void;
  loading?: boolean;
  powerData?: PowerStateResponse | any;
}

export const PowerActionsCard: React.FC<PowerActionsCardProps> = ({
  onReboot,
  onPoweroff,
  onSuspend,
}) => {
  return (
    <div>
      <h3
        style={{
          margin: '0 0 14px 0',
          fontSize: '1rem',
          fontWeight: 600,
          color: 'var(--text-primary)',
        }}
      >
        Immediate System Operations
      </h3>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '16px',
        }}
      >
        {/* Reboot Card */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            background: 'linear-gradient(180deg, rgba(56, 189, 248, 0.05) 0%, rgba(20, 20, 30, 0.6) 100%)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <RotateCw size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>System Reboot</h4>
                <span style={{ fontSize: '0.75rem', color: '#38bdf8' }}>Clean daemon restart</span>
              </div>
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                margin: 0,
              }}
            >
              Restart the kernel and OS. All systemd services stop cleanly and restart automatically
              upon boot.
            </p>
          </div>
          <div style={{ marginTop: '20px' }}>
            <button
              className="btn btn-secondary"
              onClick={onReboot}
              style={{
                width: '100%',
                borderColor: 'rgba(56, 189, 248, 0.4)',
                color: '#38bdf8',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <RotateCw size={14} />
              <span>Reboot System</span>
            </button>
          </div>
        </div>

        {/* Power Off Card */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            border: '1px solid rgba(239, 68, 68, 0.25)',
            background: 'linear-gradient(180deg, rgba(239, 68, 68, 0.05) 0%, rgba(20, 20, 30, 0.6) 100%)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  color: 'var(--red)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Power size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Power Off</h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--red)' }}>Halt hardware</span>
              </div>
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                margin: 0,
              }}
            >
              Halt kernel and power down motherboard. Turning device back on requires pressing the
              physical power switch.
            </p>
          </div>
          <div style={{ marginTop: '20px' }}>
            <button
              className="btn btn-danger"
              onClick={onPoweroff}
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Power size={14} />
              <span>Power Off Device</span>
            </button>
          </div>
        </div>

        {/* Suspend Card */}
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            border: '1px solid rgba(245, 158, 11, 0.25)',
            background: 'linear-gradient(180deg, rgba(245, 158, 11, 0.05) 0%, rgba(20, 20, 30, 0.6) 100%)',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div
                style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: 'var(--yellow)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Moon size={18} />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>Suspend to RAM</h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--yellow)' }}>Low-power sleep</span>
              </div>
            </div>
            <p
              style={{
                fontSize: '0.85rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.5,
                margin: 0,
              }}
            >
              Place device into ACPI S3 sleep. Note: WiFi & SSH will disconnect; wake-up requires
              physical button trigger.
            </p>
          </div>
          <div style={{ marginTop: '20px' }}>
            <button
              className="btn btn-secondary"
              onClick={onSuspend}
              style={{
                width: '100%',
                borderColor: 'rgba(245, 158, 11, 0.4)',
                color: 'var(--yellow)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <Moon size={14} />
              <span>Suspend to RAM</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

