import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Power,
  RotateCw,
  Moon,
  Zap,
  Clock,
  Leaf,
  Sliders,
  Flame,
  AlertTriangle,
  RefreshCw,
  ShieldAlert,
  CheckCircle2,
} from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

interface ScheduledPowerState {
  scheduled: boolean;
  action?: string;
  target_time?: string;
  minutes?: number;
  details?: string | null;
}

interface PowerStateData {
  active_governor: string;
  available_governors: string[];
  scheduled?: ScheduledPowerState | null;
}

export const PowerPage: React.FC = () => {
  const { isElevated, openElevationModal } = useAuth();
  const { addToast } = useToast();

  const [powerData, setPowerData] = useState<PowerStateData>({
    active_governor: 'unknown',
    available_governors: [],
    scheduled: null,
  });
  const [loading, setLoading] = useState(true);
  const [applyingGov, setApplyingGov] = useState<string | null>(null);

  // Custom schedule form state
  const [schedAction, setSchedAction] = useState<'reboot' | 'poweroff'>('reboot');
  const [schedMinutes, setSchedMinutes] = useState<number>(15);
  const [schedMessage, setSchedMessage] = useState<string>('Scheduled from Lavender dashboard');
  const [scheduling, setScheduling] = useState(false);

  // Modals state
  const [showRebootModal, setShowRebootModal] = useState(false);
  const [showPoweroffModal, setShowPoweroffModal] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);

  // Reboot reconnect poller state
  const [isRebooting, setIsRebooting] = useState(false);
  const [rebootAttempt, setRebootAttempt] = useState(0);
  const [deviceReconnected, setDeviceReconnected] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPowerState = useCallback(async () => {
    try {
      const data = await api.get<PowerStateData>('/api/power/state');
      setPowerData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query power state';
      addToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchPowerState();
  }, [fetchPowerState]);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Governor switching
  const handleSelectGovernor = async (gov: string) => {
    if (gov === powerData.active_governor || applyingGov) return;
    setApplyingGov(gov);
    try {
      await api.post(`/api/power/governor?governor=${encodeURIComponent(gov)}`);
      addToast(`CPU governor changed to ${gov}`, 'success');
      await fetchPowerState();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to switch to ${gov}`;
      addToast(msg, 'error');
    } finally {
      setApplyingGov(null);
    }
  };

  // Schedule action
  const handleSchedule = async (action: 'reboot' | 'poweroff', minutes: number, message?: string) => {
    setScheduling(true);
    try {
      await api.post('/api/power/schedule', {
        action,
        minutes,
        message: message || `Scheduled ${action} from Lavender dashboard`,
      });
      addToast(
        `${action.charAt(0).toUpperCase() + action.slice(1)} scheduled in ${minutes} minutes`,
        'success'
      );
      await fetchPowerState();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to schedule power action';
      addToast(msg, 'error');
    } finally {
      setScheduling(false);
    }
  };

  // Cancel scheduled action
  const handleCancelScheduled = async () => {
    try {
      await api.post('/api/power/cancel-scheduled');
      addToast('Scheduled power action canceled', 'success');
      await fetchPowerState();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to cancel scheduled action';
      addToast(msg, 'error');
    }
  };

  // Immediate Lifecycle: Reboot
  const handleConfirmReboot = async () => {
    try {
      await api.post('/api/power/reboot');
      setIsRebooting(true);
      startRebootPolling();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Reboot request failed';
      addToast(msg, 'error');
      setShowRebootModal(false);
    }
  };

  const startRebootPolling = () => {
    let attempts = 0;
    const maxAttempts = 60;

    // Wait 5 seconds before first ping
    setTimeout(() => {
      pollIntervalRef.current = setInterval(async () => {
        attempts += 1;
        setRebootAttempt(attempts);

        try {
          const res = await fetch('/api/power/state', { cache: 'no-store' });
          if (res.ok) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setDeviceReconnected(true);
            setTimeout(() => {
              window.location.reload();
            }, 1500);
          }
        } catch {
          // System still rebooting
        }

        if (attempts >= maxAttempts) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      }, 2500);
    }, 5000);
  };

  // Immediate Lifecycle: Power Off
  const handleConfirmPoweroff = async () => {
    try {
      await api.post('/api/power/poweroff');
      setShowPoweroffModal(false);
      addToast('Device is powering off completely. Lavender will disconnect.', 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Power off request failed';
      addToast(msg, 'error');
      setShowPoweroffModal(false);
    }
  };

  // Immediate Lifecycle: Suspend
  const handleConfirmSuspend = async () => {
    try {
      await api.post('/api/power/suspend');
      setShowSuspendModal(false);
      addToast('Device has entered low-power sleep state.', 'info');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Suspend request failed';
      addToast(msg, 'error');
      setShowSuspendModal(false);
    }
  };

  const isPowersaveAvail = powerData.available_governors.includes('powersave');
  const isPerfAvail = powerData.available_governors.includes('performance');
  const balancedGov = powerData.available_governors.includes('schedutil')
    ? 'schedutil'
    : powerData.available_governors.includes('ondemand')
    ? 'ondemand'
    : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Header Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'rgba(124, 58, 237, 0.15)',
              border: '1px solid rgba(124, 58, 237, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--purple)',
            }}
          >
            <Power size={22} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>
              Power & Lifecycle Management
            </h2>
            <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Hardware lifecycle operations, CPU energy scaling profiles, and timed scheduled actions
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isElevated ? (
            <span
              className="badge badge-lavender"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                fontSize: '0.85rem',
              }}
            >
              <CheckCircle2 size={14} color="var(--purple)" />
              Admin Active
            </span>
          ) : (
            <button
              className="btn btn-secondary"
              onClick={openElevationModal}
              title="Elevate privileges for power management"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                border: '1px solid rgba(124, 58, 237, 0.4)',
              }}
            >
              <ShieldAlert size={14} color="var(--purple)" />
              <span>Elevate to Admin</span>
            </button>
          )}

          <button
            className="btn btn-secondary"
            onClick={fetchPowerState}
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Warning Banner */}
      <div
        className="card"
        style={{
          borderLeft: '4px solid #f59e0b',
          background: 'rgba(245, 158, 11, 0.06)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '14px',
          padding: '16px 20px',
        }}
      >
        <AlertTriangle size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontWeight: 600, color: '#f59e0b', fontSize: '0.95rem' }}>
            Destructive System Operations
          </div>
          <p
            style={{
              margin: '4px 0 0 0',
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
          >
            These actions immediately impact the operating system. Active services, user sessions,
            network connections, and background batch jobs will terminate without checkpointing.
          </p>
        </div>
      </div>

      {/* Section 1: Immediate System Power Operations */}
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
                onClick={() => setShowRebootModal(true)}
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
                onClick={() => setShowPoweroffModal(true)}
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
                onClick={() => setShowSuspendModal(true)}
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

      {/* Section 2: CPU Frequency Profiles */}
      <div className="card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '8px',
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Zap size={20} color="var(--purple)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
              CPU Frequency Scaling Profiles
            </h3>
          </div>
          <span
            className="badge badge-lavender"
            style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
          >
            Active: {powerData.active_governor}
          </span>
        </div>
        <p
          style={{
            fontSize: '0.85rem',
            color: 'var(--text-secondary)',
            margin: '0 0 16px 0',
            lineHeight: 1.4,
          }}
        >
          Select a kernel frequency governor to optimize battery endurance, thermal dissipation, or
          peak computing performance.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '16px',
          }}
        >
          {/* Powersave */}
          <div
            className="card"
            style={{
              padding: '16px',
              border:
                powerData.active_governor === 'powersave'
                  ? '1px solid var(--green)'
                  : '1px solid var(--border)',
              background:
                powerData.active_governor === 'powersave'
                  ? 'rgba(34, 197, 94, 0.08)'
                  : 'rgba(255, 255, 255, 0.01)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '10px',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: 'rgba(34, 197, 94, 0.15)',
                    color: 'var(--green)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Leaf size={16} />
                </div>
                {powerData.active_governor === 'powersave' ? (
                  <span className="badge badge-success">Active</span>
                ) : isPowersaveAvail ? (
                  <span className="badge">Available</span>
                ) : (
                  <span className="badge" style={{ opacity: 0.5 }}>
                    Unsupported
                  </span>
                )}
              </div>
              <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', fontWeight: 600 }}>
                Power Saver <span style={{ color: 'var(--text-muted)' }}>(powersave)</span>
              </h4>
              <p
                style={{
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4,
                  margin: 0,
                }}
              >
                Pins CPU to minimum frequency. Drastically cuts power draw, maximizes battery
                runtimes, and keeps thermals cool.
              </p>
            </div>
            <div style={{ marginTop: '16px' }}>
              <button
                className={`btn ${
                  powerData.active_governor === 'powersave' ? 'btn-primary' : 'btn-secondary'
                }`}
                disabled={
                  !isPowersaveAvail ||
                  powerData.active_governor === 'powersave' ||
                  applyingGov !== null
                }
                onClick={() => handleSelectGovernor('powersave')}
                style={{ width: '100%', fontSize: '0.85rem' }}
              >
                {powerData.active_governor === 'powersave'
                  ? 'Currently Active'
                  : isPowersaveAvail
                  ? 'Activate Power Saver'
                  : 'Not Supported'}
              </button>
            </div>
          </div>

          {/* Balanced */}
          <div
            className="card"
            style={{
              padding: '16px',
              border:
                powerData.active_governor === balancedGov
                  ? '1px solid var(--purple)'
                  : '1px solid var(--border)',
              background:
                powerData.active_governor === balancedGov
                  ? 'rgba(124, 58, 237, 0.08)'
                  : 'rgba(255, 255, 255, 0.01)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '10px',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: 'rgba(124, 58, 237, 0.15)',
                    color: 'var(--purple)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Sliders size={16} />
                </div>
                {powerData.active_governor === balancedGov ? (
                  <span className="badge badge-lavender">Active</span>
                ) : balancedGov ? (
                  <span className="badge">Available</span>
                ) : (
                  <span className="badge" style={{ opacity: 0.5 }}>
                    Unsupported
                  </span>
                )}
              </div>
              <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', fontWeight: 600 }}>
                Balanced <span style={{ color: 'var(--text-muted)' }}>({balancedGov || 'schedutil'})</span>
              </h4>
              <p
                style={{
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4,
                  margin: 0,
                }}
              >
                Dynamically clocks frequencies based on CPU task load. High responsiveness under load,
                conserves power when idle.
              </p>
            </div>
            <div style={{ marginTop: '16px' }}>
              <button
                className={`btn ${
                  powerData.active_governor === balancedGov ? 'btn-primary' : 'btn-secondary'
                }`}
                disabled={
                  !balancedGov ||
                  powerData.active_governor === balancedGov ||
                  applyingGov !== null
                }
                onClick={() => balancedGov && handleSelectGovernor(balancedGov)}
                style={{ width: '100%', fontSize: '0.85rem' }}
              >
                {powerData.active_governor === balancedGov
                  ? 'Currently Active'
                  : balancedGov
                  ? 'Activate Balanced'
                  : 'Not Supported'}
              </button>
            </div>
          </div>

          {/* Performance */}
          <div
            className="card"
            style={{
              padding: '16px',
              border:
                powerData.active_governor === 'performance'
                  ? '1px solid var(--yellow)'
                  : '1px solid var(--border)',
              background:
                powerData.active_governor === 'performance'
                  ? 'rgba(245, 158, 11, 0.08)'
                  : 'rgba(255, 255, 255, 0.01)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '10px',
                }}
              >
                <div
                  style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: 'rgba(245, 158, 11, 0.15)',
                    color: 'var(--yellow)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Flame size={16} />
                </div>
                {powerData.active_governor === 'performance' ? (
                  <span className="badge badge-warning">Active</span>
                ) : isPerfAvail ? (
                  <span className="badge">Available</span>
                ) : (
                  <span className="badge" style={{ opacity: 0.5 }}>
                    Unsupported
                  </span>
                )}
              </div>
              <h4 style={{ margin: '0 0 6px 0', fontSize: '0.95rem', fontWeight: 600 }}>
                High Performance <span style={{ color: 'var(--text-muted)' }}>(performance)</span>
              </h4>
              <p
                style={{
                  fontSize: '0.8rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.4,
                  margin: 0,
                }}
              >
                Locks all cores to maximum clock speed. Eliminates ramp-up latency for compiling, heavy
                computations, or benchmarks.
              </p>
            </div>
            <div style={{ marginTop: '16px' }}>
              <button
                className={`btn ${
                  powerData.active_governor === 'performance' ? 'btn-primary' : 'btn-secondary'
                }`}
                disabled={
                  !isPerfAvail ||
                  powerData.active_governor === 'performance' ||
                  applyingGov !== null
                }
                onClick={() => handleSelectGovernor('performance')}
                style={{ width: '100%', fontSize: '0.85rem' }}
              >
                {powerData.active_governor === 'performance'
                  ? 'Currently Active'
                  : isPerfAvail
                  ? 'Activate Performance'
                  : 'Not Supported'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Scheduled Power Actions */}
      <div className="card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '16px',
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Clock size={20} color="var(--purple)" />
            <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 600 }}>
              Scheduled Power Actions
            </h3>
          </div>
          {powerData.scheduled?.scheduled ? (
            <span className="badge badge-warning">Pending Action</span>
          ) : (
            <span className="badge">No Actions</span>
          )}
        </div>

        {/* Pending schedule status banner */}
        {powerData.scheduled?.scheduled ? (
          <div
            style={{
              padding: '14px 18px',
              borderRadius: 'var(--radius)',
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '20px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <AlertTriangle size={18} color="#f59e0b" />
              <span style={{ fontSize: '0.9rem', color: '#f59e0b', fontWeight: 600 }}>
                {powerData.scheduled.details || 'A timed power action is currently pending'}
              </span>
            </div>
            <button
              className="btn btn-danger"
              onClick={handleCancelScheduled}
              style={{ fontSize: '0.85rem', padding: '6px 12px' }}
            >
              Cancel Scheduled Action
            </button>
          </div>
        ) : (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border)',
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Clock size={16} />
            <span>No pending reboot or shutdown operations are currently scheduled.</span>
          </div>
        )}

        {/* Quick Timers */}
        <div style={{ marginBottom: '20px' }}>
          <div
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '10px',
            }}
          >
            Quick Scheduling Presets:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              disabled={scheduling}
              onClick={() => handleSchedule('reboot', 5)}
              style={{ fontSize: '0.85rem' }}
            >
              Reboot in 5m
            </button>
            <button
              className="btn btn-secondary"
              disabled={scheduling}
              onClick={() => handleSchedule('reboot', 15)}
              style={{ fontSize: '0.85rem' }}
            >
              Reboot in 15m
            </button>
            <button
              className="btn btn-secondary"
              disabled={scheduling}
              onClick={() => handleSchedule('reboot', 30)}
              style={{ fontSize: '0.85rem' }}
            >
              Reboot in 30m
            </button>
            <button
              className="btn btn-secondary"
              disabled={scheduling}
              onClick={() => handleSchedule('reboot', 60)}
              style={{ fontSize: '0.85rem' }}
            >
              Reboot in 1h
            </button>
            <button
              className="btn btn-secondary"
              disabled={scheduling}
              onClick={() => handleSchedule('poweroff', 15)}
              style={{ fontSize: '0.85rem' }}
            >
              Power Off in 15m
            </button>
          </div>
        </div>

        {/* Custom Schedule Form */}
        <div
          style={{
            padding: '16px',
            borderRadius: 'var(--radius)',
            background: 'rgba(255, 255, 255, 0.015)',
            border: '1px solid var(--border)',
          }}
        >
          <div
            style={{
              fontSize: '0.85rem',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              marginBottom: '12px',
            }}
          >
            Custom Timed Action:
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSchedule(schedAction, schedMinutes, schedMessage);
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <select
              className="input"
              value={schedAction}
              onChange={(e) => setSchedAction(e.target.value as 'reboot' | 'poweroff')}
              style={{ width: '130px', padding: '6px 10px', fontSize: '0.85rem' }}
            >
              <option value="reboot">Reboot</option>
              <option value="poweroff">Power Off</option>
            </select>

            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>in</span>

            <input
              type="number"
              className="input"
              min={1}
              max={1440}
              value={schedMinutes}
              onChange={(e) => setSchedMinutes(parseInt(e.target.value, 10) || 1)}
              style={{ width: '90px', padding: '6px 10px', fontSize: '0.85rem' }}
              required
            />

            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>minutes</span>

            <input
              type="text"
              className="input"
              placeholder="Broadcast message (optional)"
              value={schedMessage}
              onChange={(e) => setSchedMessage(e.target.value)}
              style={{ flex: '1 1 200px', padding: '6px 10px', fontSize: '0.85rem' }}
            />

            <button
              type="submit"
              className="btn btn-primary"
              disabled={scheduling}
              style={{ padding: '7px 18px', fontSize: '0.85rem' }}
            >
              {scheduling ? 'Scheduling...' : 'Schedule'}
            </button>
          </form>
        </div>
      </div>

      {/* Reboot Modal / Reconnect Poller */}
      {showRebootModal && (
        <div
          role="dialog"
          aria-modal="true"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '440px',
              padding: '24px',
              background: '#0d0d14',
              border: '1px solid rgba(56, 189, 248, 0.4)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
            }}
          >
            {!isRebooting ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                  <div
                    style={{
                      width: '38px',
                      height: '38px',
                      borderRadius: '8px',
                      background: 'rgba(56, 189, 248, 0.15)',
                      color: '#38bdf8',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <RotateCw size={20} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>
                    Confirm System Reboot
                  </h3>
                </div>

                <p
                  style={{
                    color: 'var(--text-secondary)',
                    fontSize: '0.9rem',
                    lineHeight: 1.5,
                    margin: '0 0 16px 0',
                  }}
                >
                  Are you sure you want to reboot the system? All active processes and network
                  connections will be terminated.
                </p>

                <div
                  style={{
                    padding: '10px 14px',
                    borderRadius: 'var(--radius)',
                    background: 'rgba(245, 158, 11, 0.08)',
                    border: '1px solid rgba(245, 158, 11, 0.25)',
                    color: '#f59e0b',
                    fontSize: '0.85rem',
                    marginBottom: '20px',
                  }}
                >
                  Lavender will reconnect automatically as soon as the kernel finishes booting.
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setShowRebootModal(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={handleConfirmReboot}
                  >
                    Proceed with Reboot
                  </button>
                </div>
              </>
            ) : (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  padding: '16px 0',
                  gap: '16px',
                }}
              >
                {!deviceReconnected ? (
                  <>
                    <LoadingSpinner size={42} />
                    <div>
                      <h4 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', fontWeight: 600 }}>
                        Rebooting System...
                      </h4>
                      <p
                        style={{
                          margin: 0,
                          fontSize: '0.85rem',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.5,
                        }}
                      >
                        Waiting for device to come back online.
                        <br />
                        {rebootAttempt > 0
                          ? `Attempt ${rebootAttempt} of 60 — pinging Lavender...`
                          : 'Lavender will re-establish session as soon as networking starts.'}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={42} color="var(--green)" />
                    <div>
                      <h4
                        style={{
                          margin: '0 0 6px 0',
                          fontSize: '1.1rem',
                          fontWeight: 600,
                          color: 'var(--green)',
                        }}
                      >
                        Device Online!
                      </h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Reloading dashboard...
                      </p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Power Off Confirm Modal */}
      <ConfirmModal
        isOpen={showPoweroffModal}
        title="Confirm Power Off"
        message="The device will shut down completely. To turn it back on, you will need physical access to press the hardware power button. This action cannot be undone remotely."
        confirmLabel="Power Off Completely"
        cancelLabel="Cancel"
        isDanger={true}
        onConfirm={handleConfirmPoweroff}
        onClose={() => setShowPoweroffModal(false)}
      />

      {/* Suspend Confirm Modal */}
      <ConfirmModal
        isOpen={showSuspendModal}
        title="Confirm Suspend to RAM"
        message="The device will enter a low-power suspend sleep state. Suspending puts WiFi and network subsystems to sleep. You will lose remote access until someone physically presses the hardware power switch."
        confirmLabel="Suspend Device"
        cancelLabel="Cancel"
        isDanger={true}
        onConfirm={handleConfirmSuspend}
        onClose={() => setShowSuspendModal(false)}
      />
    </div>
  );
};
