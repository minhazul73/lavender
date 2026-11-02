import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Power, RotateCw, AlertTriangle, RefreshCw, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { ConfirmModal } from '../../components/common/ConfirmModal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { PowerActionsCard } from './PowerActionsCard';
import { CpuGovernorCard } from './CpuGovernorCard';
import { ScheduledPowerCard, ScheduledPowerState } from './ScheduledPowerCard';

interface PowerStateData {
  active_governor: string;
  available_governors: string[];
  scheduled?: ScheduledPowerState | null;
}

export const PowerPage: React.FC = () => {
  const { isElevated, openElevationModal } = useAuth();
  const { addToast } = useToast();

  const [powerData, setPowerData] = useState<PowerStateData>({ active_governor: 'unknown', available_governors: [], scheduled: null });
  const [loading, setLoading] = useState(true);
  const [applyingGov, setApplyingGov] = useState<string | null>(null);
  const [scheduling, setScheduling] = useState(false);

  // Modals and reconnect state
  const [showRebootModal, setShowRebootModal] = useState(false);
  const [showPoweroffModal, setShowPoweroffModal] = useState(false);
  const [showSuspendModal, setShowSuspendModal] = useState(false);
  const [isRebooting, setIsRebooting] = useState(false);
  const [rebootAttempt, setRebootAttempt] = useState(0);
  const [deviceReconnected, setDeviceReconnected] = useState(false);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchPowerState = useCallback(async () => {
    try {
      const data = await api.get<PowerStateData>('/api/power/state');
      setPowerData(data);
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to query power state', 'error');
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    fetchPowerState();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [fetchPowerState]);

  // Governor switching
  const handleSelectGovernor = async (gov: string) => {
    if (gov === powerData.active_governor || applyingGov) return;
    setApplyingGov(gov);
    try {
      await api.post(`/api/power/governor?governor=${encodeURIComponent(gov)}`);
      addToast(`CPU governor changed to ${gov}`, 'success');
      await fetchPowerState();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : `Failed to switch to ${gov}`, 'error');
    } finally {
      setApplyingGov(null);
    }
  };

  // Schedule action
  const handleSchedule = async (action: 'reboot' | 'poweroff', minutes: number, message?: string) => {
    setScheduling(true);
    try {
      await api.post('/api/power/schedule', { action, minutes, message: message || `Scheduled ${action} from Lavender dashboard` });
      addToast(`${action.charAt(0).toUpperCase() + action.slice(1)} scheduled in ${minutes} minutes`, 'success');
      await fetchPowerState();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Failed to schedule power action', 'error');
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
      addToast(err instanceof Error ? err.message : 'Failed to cancel scheduled action', 'error');
    }
  };

  // Immediate Lifecycle: Reboot
  const handleConfirmReboot = async () => {
    try {
      await api.post('/api/power/reboot');
      setIsRebooting(true);
      startRebootPolling();
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Reboot request failed', 'error');
      setShowRebootModal(false);
    }
  };

  const startRebootPolling = () => {
    let attempts = 0;
    const maxAttempts = 60;
    setTimeout(() => {
      pollIntervalRef.current = setInterval(async () => {
        attempts += 1;
        setRebootAttempt(attempts);
        try {
          const res = await fetch('/api/power/state', { cache: 'no-store' });
          if (res.ok) {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            setDeviceReconnected(true);
            setTimeout(() => { window.location.reload(); }, 1500);
          }
        } catch {
          // System still rebooting
        }
        if (attempts >= maxAttempts && pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      }, 2500);
    }, 5000);
  };

  // Immediate Lifecycle: Power Off & Suspend
  const handleConfirmPoweroff = async () => {
    try {
      await api.post('/api/power/poweroff');
      setShowPoweroffModal(false);
      addToast('Device is powering off completely. Lavender will disconnect.', 'info');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Power off request failed', 'error');
      setShowPoweroffModal(false);
    }
  };

  const handleConfirmSuspend = async () => {
    try {
      await api.post('/api/power/suspend');
      setShowSuspendModal(false);
      addToast('Device has entered low-power sleep state.', 'info');
    } catch (err: unknown) {
      addToast(err instanceof Error ? err.message : 'Suspend request failed', 'error');
      setShowSuspendModal(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Header Strip */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'rgba(124, 58, 237, 0.15)', border: '1px solid rgba(124, 58, 237, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--purple)' }}>
            <Power size={22} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700 }}>Power & Lifecycle Management</h2>
            <p style={{ margin: '2px 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Hardware lifecycle operations, CPU energy scaling profiles, and timed scheduled actions
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isElevated ? (
            <span className="badge badge-lavender" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.85rem' }}>
              <CheckCircle2 size={14} color="var(--purple)" />
              Admin Active
            </span>
          ) : (
            <button className="btn btn-secondary" onClick={openElevationModal} title="Elevate privileges for power management" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', border: '1px solid rgba(124, 58, 237, 0.4)' }}>
              <ShieldAlert size={14} color="var(--purple)" />
              <span>Elevate to Admin</span>
            </button>
          )}

          <button className="btn btn-secondary" onClick={fetchPowerState} disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="card" style={{ borderLeft: '4px solid #f59e0b', background: 'rgba(245, 158, 11, 0.06)', display: 'flex', alignItems: 'flex-start', gap: '14px', padding: '16px 20px' }}>
        <AlertTriangle size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontWeight: 600, color: '#f59e0b', fontSize: '0.95rem' }}>Destructive System Operations</div>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            These actions immediately impact the operating system. Active services, user sessions, network connections, and background batch jobs will terminate without checkpointing.
          </p>
        </div>
      </div>

      {/* Section 1: Immediate System Power Operations */}
      <PowerActionsCard
        onReboot={() => setShowRebootModal(true)}
        onPoweroff={() => setShowPoweroffModal(true)}
        onSuspend={() => setShowSuspendModal(true)}
        loading={loading}
      />
      <CpuGovernorCard
        activeGovernor={powerData.active_governor}
        availableGovernors={powerData.available_governors}
        onSelectGovernor={handleSelectGovernor}
        applying={applyingGov !== null}
      />
      <ScheduledPowerCard
        scheduledState={powerData.scheduled}
        onSchedule={handleSchedule}
        onCancelScheduled={handleCancelScheduled}
        actionPending={scheduling}
      />

      {/* Reboot Modal / Reconnect Poller */}
      {showRebootModal && (
        <div role="dialog" aria-modal="true" style={{ position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.75)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div className="card" style={{ width: '100%', maxWidth: '440px', padding: '24px', background: '#0d0d14', border: '1px solid rgba(56, 189, 248, 0.4)', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)' }}>
            {!isRebooting ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                  <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <RotateCw size={20} />
                  </div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>Confirm System Reboot</h3>
                </div>

                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                  Are you sure you want to reboot the system? All active processes and network connections will be terminated.
                </p>

                <div style={{ padding: '10px 14px', borderRadius: 'var(--radius)', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', color: '#f59e0b', fontSize: '0.85rem', marginBottom: '20px' }}>
                  Lavender will reconnect automatically as soon as the kernel finishes booting.
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button className="btn btn-secondary" onClick={() => setShowRebootModal(false)}>Cancel</button>
                  <button className="btn btn-danger" onClick={handleConfirmReboot}>Proceed with Reboot</button>
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '16px 0', gap: '16px' }}>
                {!deviceReconnected ? (
                  <>
                    <LoadingSpinner size={42} />
                    <div>
                      <h4 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', fontWeight: 600 }}>Rebooting System...</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                        Waiting for device to come back online.
                        <br />
                        {rebootAttempt > 0 ? `Attempt ${rebootAttempt} of 60 — pinging Lavender...` : 'Lavender will re-establish session as soon as networking starts.'}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={42} color="var(--green)" />
                    <div>
                      <h4 style={{ margin: '0 0 6px 0', fontSize: '1.1rem', fontWeight: 600, color: 'var(--green)' }}>Device Online!</h4>
                      <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Reloading dashboard...</p>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
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
